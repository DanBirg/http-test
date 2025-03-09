#!/usr/bin/env python3
import requests
import time
import argparse
import random
import threading
import concurrent.futures
import queue
import signal
import sys

# Global variables for statistics
total_requests = 0
successful_requests = 0
failed_requests = 0
stats_lock = threading.Lock()
running = True
start_time = None

def worker(server_ip, path, timeout, thread_id, stats_queue):
    """Worker function for each thread to send requests"""
    global running, total_requests, successful_requests, failed_requests
    
    url = f"http://{server_ip}{path}"
    session = requests.Session()  # Use session for connection pooling
    local_count = 0
    
    while running:
        try:
            response = session.get(url, timeout=timeout)
            status_code = response.status_code
            
            with stats_lock:
                total_requests += 1
                local_count += 1
                if 200 <= status_code < 400:
                    successful_requests += 1
                else:
                    failed_requests += 1
            
            # Optionally enqueue detailed stats
            if stats_queue is not None:
                stats_queue.put((thread_id, status_code, time.time()))
                
        except requests.exceptions.RequestException:
            with stats_lock:
                total_requests += 1
                local_count += 1
                failed_requests += 1

def stats_reporter(interval, stats_queue):
    """Thread to periodically report statistics"""
    global running, total_requests, successful_requests, failed_requests, start_time
    
    last_total = 0
    last_time = time.time()
    
    while running:
        time.sleep(interval)
        current_time = time.time()
        current_total = total_requests
        
        elapsed = current_time - last_time
        requests_since_last = current_total - last_total
        rps = requests_since_last / elapsed if elapsed > 0 else 0
        
        total_elapsed = current_time - start_time
        total_rps = current_total / total_elapsed if total_elapsed > 0 else 0
        
        success_rate = (successful_requests / current_total * 100) if current_total > 0 else 0
        
        print(f"\r[STATS] Requests: {current_total} | "
              f"Rate: {rps:.2f} req/s | "
              f"Avg: {total_rps:.2f} req/s | "
              f"Success: {success_rate:.1f}% | "
              f"Threads: {threading.active_count()-1}", end="")
        
        sys.stdout.flush()
        last_total = current_total
        last_time = current_time

def handle_sigint(signum, frame):
    """Handle interrupt signal (Ctrl+C)"""
    global running
    print("\n\nShutting down, please wait for threads to complete...")
    running = False

def send_load(server_ip, path="/", threads=50, timeout=3, report_interval=1.0, detailed=False):
    """
    Send massive HTTP load using multiple threads
    
    Parameters:
    - server_ip: IP address of the target server
    - path: HTTP path to request
    - threads: Number of concurrent threads
    - timeout: Request timeout in seconds
    - report_interval: How often to report statistics
    - detailed: Whether to collect detailed per-request stats
    """
    global running, start_time, total_requests, successful_requests, failed_requests
    
    # Reset global stats
    total_requests = 0
    successful_requests = 0
    failed_requests = 0
    running = True
    start_time = time.time()
    
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, handle_sigint)
    
    # Create stats queue if detailed reporting is enabled
    stats_queue = queue.Queue(maxsize=10000) if detailed else None
    
    print(f"Starting load test against http://{server_ip}{path}")
    print(f"Using {threads} concurrent threads")
    print("Press Ctrl+C to stop the test\n")
    
    # Start reporter thread
    reporter_thread = threading.Thread(target=stats_reporter, args=(report_interval, stats_queue))
    reporter_thread.daemon = True
    reporter_thread.start()
    
    # Start worker threads
    worker_threads = []
    for i in range(threads):
        t = threading.Thread(target=worker, args=(server_ip, path, timeout, i, stats_queue))
        t.daemon = True
        t.start()
        worker_threads.append(t)
    
    # Wait for SIGINT or other termination
    try:
        while running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        running = False
    
    # Wait for threads to finish
    for t in worker_threads:
        t.join(timeout=1.0)
    
    # Final report
    end_time = time.time()
    total_time = end_time - start_time
    final_rps = total_requests / total_time if total_time > 0 else 0
    
    print("\n\n--- Final Results ---")
    print(f"Total requests:    {total_requests}")
    print(f"Successful:        {successful_requests} ({successful_requests/total_requests*100:.1f}%)")
    print(f"Failed:            {failed_requests} ({failed_requests/total_requests*100:.1f}%)")
    print(f"Total time:        {total_time:.2f} seconds")
    print(f"Average rate:      {final_rps:.2f} requests/second")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='High-performance HTTP load generator')
    parser.add_argument('server_ip', help='IP address of the target server')
    parser.add_argument('--path', default='/', help='HTTP path to request (default: /)')
    parser.add_argument('--threads', type=int, default=50, help='Number of concurrent threads (default: 50)')
    parser.add_argument('--timeout', type=float, default=3.0, help='Request timeout in seconds (default: 3.0)')
    parser.add_argument('--report-interval', type=float, default=1.0, help='Stats reporting interval in seconds (default: 1.0)')
    parser.add_argument('--detailed', action='store_true', help='Collect detailed per-request statistics')
    
    args = parser.parse_args()
    
    send_load(args.server_ip, args.path, args.threads, args.timeout, args.report_interval, args.detailed)
