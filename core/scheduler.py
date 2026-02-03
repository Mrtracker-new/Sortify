from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
import logging
from pathlib import Path
import threading
import time
from datetime import datetime

class SortScheduler:
    """Enhanced scheduler for automated sorting tasks with improved reliability and features"""
    def __init__(self, file_ops, categorizer):
        self.scheduler = BackgroundScheduler()
        self.file_ops = file_ops
        self.categorizer = categorizer
        self.jobs = {}
        self.job_history = {}
        self.max_history_per_job = 10
        self.recursive_sort = False  # Default to non-recursive sorting
        
        # Set up event listeners for job execution
        self.scheduler.add_listener(self._job_executed_event, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error_event, EVENT_JOB_ERROR)
        
    def start(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logging.info("Scheduler started")
            
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logging.info("Scheduler stopped")
            
    def add_job(self, folder_path, name, trigger_type='daily', day_of_week=None, 
                hour=0, minute=0, day=1, interval_minutes=None, recursive=False):
        """Add a scheduled sorting job with enhanced options
        
        Args:
            folder_path: Path to the folder to sort
            name: Name for this job
            trigger_type: 'daily', 'weekly', 'monthly', or 'interval'
            day_of_week: Day of week for weekly trigger (0-6, where 0=Monday)
            hour: Hour to run (0-23)
            minute: Minute to run (0-59)
            day: Day of month for monthly trigger (1-31)
            interval_minutes: Minutes between runs for interval trigger
            recursive: Whether to sort files in subfolders recursively
        """
        folder_path = Path(folder_path)
        
        if not folder_path.exists() or not folder_path.is_dir():
            logging.error(f"Cannot schedule job for non-existent directory: {folder_path}")
            return False
            
        # Remove any existing job with this name
        if name in self.jobs:
            self.remove_job(name)
            
        # Configure the trigger based on type
        if trigger_type == 'interval' and interval_minutes is not None:
            trigger = IntervalTrigger(minutes=interval_minutes)
            schedule_desc = f"every {interval_minutes} minutes"
        elif trigger_type == 'daily':
            trigger = CronTrigger(hour=hour, minute=minute)
            schedule_desc = f"daily at {hour:02d}:{minute:02d}"
        elif trigger_type == 'weekly':
            if day_of_week is None:
                day_of_week = 0  # Default to Monday
            trigger = CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute)
            days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            schedule_desc = f"weekly on {days[day_of_week]} at {hour:02d}:{minute:02d}"
        elif trigger_type == 'monthly':
            trigger = CronTrigger(day=day, hour=hour, minute=minute)
            schedule_desc = f"monthly on day {day} at {hour:02d}:{minute:02d}"
        else:
            logging.error(f"Unknown trigger type: {trigger_type}")
            return False
            
        # Add the job to the scheduler
        job = self.scheduler.add_job(
            self._sort_folder,
            trigger=trigger,
            args=[folder_path, recursive, name],
            id=name,
            replace_existing=True
        )
        
        # Store job info
        self.jobs[name] = {
            'job': job,
            'folder_path': str(folder_path),
            'schedule': schedule_desc,
            'trigger_type': trigger_type,
            'recursive': recursive,
            'created_at': datetime.now(),
            'last_run': None,
            'next_run': job.next_run_time,
            'run_count': 0,
            'error_count': 0
        }
        
        # Initialize job history
        self.job_history[name] = []
        
        logging.info(f"Scheduled sorting job '{name}' for {folder_path} {schedule_desc} (recursive={recursive})")
        return True
    
    def add_one_time_job(self, folder_path, name, run_date=None, recursive=False):
        """Add a one-time sorting job
        
        Args:
            folder_path: Path to the folder to sort
            name: Name for this job
            run_date: Datetime to run the job (None for immediate execution)
            recursive: Whether to sort files in subfolders recursively
        """
        folder_path = Path(folder_path)
        
        if not folder_path.exists() or not folder_path.is_dir():
            logging.error(f"Cannot schedule job for non-existent directory: {folder_path}")
            return False
            
        # Remove any existing job with this name
        if name in self.jobs:
            self.remove_job(name)
        
        if run_date is None:
            # Run immediately in a separate thread
            threading.Thread(target=self._sort_folder, args=[folder_path, recursive, name]).start()
            schedule_desc = "immediately (one-time)"
            
            # Store job info without actual job object
            self.jobs[name] = {
                'job': None,  # No actual job in scheduler
                'folder_path': str(folder_path),
                'schedule': schedule_desc,
                'trigger_type': 'one-time',
                'recursive': recursive,
                'created_at': datetime.now(),
                'last_run': datetime.now(),
                'next_run': None,
                'run_count': 1,
                'error_count': 0
            }
        else:
            # Schedule for future execution
            job = self.scheduler.add_job(
                self._sort_folder,
                'date',
                run_date=run_date,
                args=[folder_path, recursive, name],
                id=name
            )
            
            schedule_desc = f"one-time at {run_date}"
            
            # Store job info
            self.jobs[name] = {
                'job': job,
                'folder_path': str(folder_path),
                'schedule': schedule_desc,
                'trigger_type': 'one-time',
                'recursive': recursive,
                'created_at': datetime.now(),
                'last_run': None,
                'next_run': run_date,
                'run_count': 0,
                'error_count': 0
            }
        
        # Initialize job history
        self.job_history[name] = []
        
        logging.info(f"Scheduled one-time sorting job '{name}' for {folder_path} {schedule_desc}")
        return True
        
    def remove_job(self, name):
        """Remove a scheduled job"""
        if name in self.jobs:
            # Only try to remove from scheduler if it's an actual scheduled job
            if self.jobs[name]['job'] is not None:
                try:
                    self.scheduler.remove_job(name)
                except Exception as e:
                    logging.warning(f"Error removing job {name} from scheduler: {e}")
            
            del self.jobs[name]
            
            # Keep the history for reference
            logging.info(f"Removed scheduled job: {name}")
            return True
        return False
    
    def pause_job(self, name):
        """Pause a scheduled job"""
        if name in self.jobs and self.jobs[name]['job'] is not None:
            self.jobs[name]['job'].pause()
            logging.info(f"Paused job: {name}")
            return True
        return False
    
    def resume_job(self, name):
        """Resume a paused job"""
        if name in self.jobs and self.jobs[name]['job'] is not None:
            self.jobs[name]['job'].resume()
            logging.info(f"Resumed job: {name}")
            return True
        return False
        
    def _sort_folder(self, folder_path, recursive=False, job_name=None):
        """Sort all files in the given folder with improved handling"""
        folder_path = Path(folder_path)
        start_time = time.time()
        files_processed = 0
        files_moved = 0
        errors = 0
        
        logging.info(f"Running scheduled sort for folder: {folder_path} (recursive={recursive})")
        
        try:
            # Get all files in the folder (recursive or non-recursive)
            if recursive:
                files = [f for f in folder_path.glob('**/*') if f.is_file()]
            else:
                files = [f for f in folder_path.iterdir() if f.is_file()]
            
            if not files:
                logging.info(f"No files found to sort in {folder_path}")
                return
                
            total_files = len(files)
            logging.info(f"Found {total_files} files to sort")
            
            # Sort each file
            for file_path in files:
                try:
                    files_processed += 1
                    
                    # Skip zero-byte files
                    if file_path.stat().st_size == 0:
                        logging.warning(f"Skipping zero-byte file: {file_path}")
                        continue
                    
                    category = self.categorizer.categorize_file(file_path)
                    
                    # Try to move the file with retry logic
                    self._move_with_retry(file_path, category)
                    files_moved += 1
                    
                except Exception as e:
                    errors += 1
                    logging.error(f"Error sorting file {file_path}: {e}")
            
            duration = time.time() - start_time
            logging.info(f"Completed scheduled sort for {folder_path}: {files_moved}/{total_files} files moved in {duration:.2f}s")
            
            # Update job statistics
            if job_name and job_name in self.jobs:
                self.jobs[job_name]['last_run'] = datetime.now()
                self.jobs[job_name]['run_count'] += 1
                
                # Add to job history
                history_entry = {
                    'timestamp': datetime.now(),
                    'duration': duration,
                    'files_processed': files_processed,
                    'files_moved': files_moved,
                    'errors': errors
                }
                
                self.job_history[job_name].append(history_entry)
                
                # Trim history if needed
                if len(self.job_history[job_name]) > self.max_history_per_job:
                    self.job_history[job_name] = self.job_history[job_name][-self.max_history_per_job:]
            
        except Exception as e:
            logging.error(f"Error during scheduled sort of {folder_path}: {e}")
            
            # Update error statistics
            if job_name and job_name in self.jobs:
                self.jobs[job_name]['error_count'] += 1
    
    def _move_with_retry(self, file_path, category):
        """Try to move a file with retry logic for locked files"""
        # Guard against None file_ops
        if self.file_ops is None:
            logging.error(f"Cannot move file {file_path}: FileOperations not initialized")
            return False
            
        max_retries = 3
        retry_delay = 1.0  # seconds
        
        for attempt in range(max_retries):
            try:
                self.file_ops.move_file(file_path, category)
                logging.info(f"Sorted {file_path.name} to {category}")
                return True
            except PermissionError:
                # File might be locked by another process
                if attempt < max_retries - 1:
                    logging.warning(f"File locked, retrying in {retry_delay}s: {file_path}")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logging.error(f"File locked after {max_retries} attempts: {file_path}")
                    raise
            except Exception as e:
                logging.error(f"Error moving file {file_path}: {e}")
                raise
    
    def _job_executed_event(self, event):
        """Handle job executed event"""
        job_id = event.job_id
        if job_id in self.jobs:
            # Update next run time
            if self.jobs[job_id]['job'] is not None:
                self.jobs[job_id]['next_run'] = self.jobs[job_id]['job'].next_run_time
    
    def _job_error_event(self, event):
        """Handle job error event"""
        job_id = event.job_id
        if job_id in self.jobs:
            self.jobs[job_id]['error_count'] += 1
            logging.error(f"Job {job_id} failed with exception: {event.exception}")
            
    def get_jobs(self):
        """Get a copy of the current jobs dictionary"""
        return self.jobs.copy()
    
    def get_job_history(self, job_name=None):
        """Get job execution history
        
        Args:
            job_name: Name of the job to get history for, or None for all jobs
        """
        if job_name:
            return self.job_history.get(job_name, [])
        return self.job_history.copy()
    
    def set_global_recursive(self, recursive):
        """Set the global recursive sorting setting"""
        self.recursive_sort = recursive
        logging.info(f"Set global recursive sorting to: {recursive}")
        
    def run_all_jobs_now(self):
        """Run all scheduled jobs immediately"""
        for name, job_info in self.jobs.items():
            if job_info['job'] is not None:  # Skip one-time jobs that have already run
                folder_path = job_info['folder_path']
                recursive = job_info['recursive']
                threading.Thread(target=self._sort_folder, 
                                args=[folder_path, recursive, name]).start()
                logging.info(f"Manually triggered job: {name}")
        return True