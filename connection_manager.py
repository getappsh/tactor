#!/usr/bin/env python3
"""
Tactical BitTorrent Connection Manager
This script monitors network connectivity and controls Transmission's behavior
based on network conditions in tactical environments with intermittent connectivity.
"""

import os
import time
import json
import logging
import subprocess
import requests
from pathlib import Path
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('connection-manager')

# Configuration
TRANSMISSION_RPC_URL = "http://localhost:9091/transmission/rpc"
TRANSMISSION_CONFIG_DIR = "/transmission-config"
CHECK_INTERVAL = 60  # Check network every 60 seconds
PING_HOSTS = ["1.1.1.1", "8.8.8.8"]  # Hosts to ping for connectivity check
RECONNECT_ATTEMPTS = 3
CONNECTION_TIMEOUT = 5  # seconds
AUTH = ("admin", "tactical_pass")  # Should match transmission settings

# Network state tracking
network_state = {
    "last_online": time.time(),
    "is_online": True,
    "connection_quality": "good",  # "good", "poor", "offline"
    "reconnect_count": 0,
    "bandwidth_mode": "normal"  # "normal", "conservative", "minimal"
}

def get_transmission_session_id() -> str:
    """Get the X-Transmission-Session-Id required for RPC calls."""
    try:
        response = requests.get(TRANSMISSION_RPC_URL, auth=AUTH, timeout=CONNECTION_TIMEOUT)
        if response.status_code == 409:
            return response.headers.get('X-Transmission-Session-Id', '')
    except requests.RequestException as e:
        logger.error(f"Failed to get session ID: {e}")
    return ''

def transmission_rpc_call(method: str, arguments: Dict = None) -> Optional[Dict]:
    """Make an RPC call to Transmission."""
    session_id = get_transmission_session_id()
    if not session_id:
        logger.error("Could not get Transmission session ID")
        return None
    
    headers = {'X-Transmission-Session-Id': session_id}
    payload = {
        "method": method,
        "arguments": arguments or {}
    }
    
    try:
        response = requests.post(
            TRANSMISSION_RPC_URL, 
            json=payload,
            headers=headers,
            auth=AUTH,
            timeout=CONNECTION_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"RPC call failed with status {response.status_code}: {response.text}")
    except requests.RequestException as e:
        logger.error(f"RPC request failed: {e}")
    
    return None

def check_network_connectivity() -> bool:
    """Check if network is reachable by pinging hosts."""
    for host in PING_HOSTS:
        try:
            # Use subprocess to ping the host with a timeout
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "2", host],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=3
            )
            if result.returncode == 0:
                return True
        except (subprocess.SubprocessError, subprocess.TimeoutExpired):
            continue
    
    return False

def measure_connection_quality() -> str:
    """Measure connection quality by checking ping times."""
    total_time = 0
    successful_pings = 0
    
    for host in PING_HOSTS:
        try:
            # Use ping to measure round-trip time
            result = subprocess.run(
                ["ping", "-c", "3", "-W", "2", host],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Extract average time from ping output
                output = result.stdout
                try:
                    # Different ping outputs have different formats
                    # Try to find numeric values in the output
                    if "min/avg/max" in output:
                        # Linux/macOS format: min/avg/max
                        parts = output.split("min/avg/max")[1].strip()
                        if "/" in parts:
                            avg_time = float(parts.split("/")[1].strip())
                            total_time += avg_time
                            successful_pings += 1
                    elif "Average" in output:
                        # Windows format: Average = X ms
                        avg_time = float(output.split("Average =")[1].split("ms")[0].strip())
                        total_time += avg_time
                        successful_pings += 1
                    else:
                        # Last resort: just find any number followed by ms
                        import re
                        times = re.findall(r'(\d+\.\d+|\d+) ms', output)
                        if times:
                            # Take average of found times
                            time_values = [float(t) for t in times]
                            avg_time = sum(time_values) / len(time_values)
                            total_time += avg_time
                            successful_pings += 1
                except (ValueError, IndexError) as e:
                    logger.warning(f"Could not parse ping output: {e}")
                    logger.debug(f"Ping output was: {output}")
                    # Count as a successful ping but with high latency
                    total_time += 1000  # Assume 1000ms as a fallback
                    successful_pings += 1
        except (subprocess.SubprocessError, subprocess.TimeoutExpired) as e:
            logger.warning(f"Ping to {host} failed: {e}")
            continue
    
    if successful_pings == 0:
        return "offline"
    
    avg_ping = total_time / successful_pings
    logger.info(f"Average ping time: {avg_ping}ms")
    
    if avg_ping < 200:
        return "good"
    elif avg_ping < 500:
        return "poor"
    else:
        return "very_poor"

def adjust_transmission_settings(connection_quality: str) -> None:
    """Adjust Transmission settings based on connection quality."""
    settings = {}
    
    if connection_quality == "offline":
        # When offline, pause all active torrents
        pause_all_torrents()
        settings = {
            "alt-speed-enabled": True,
            "alt-speed-down": 10,
            "alt-speed-up": 1,
            "download-queue-size": 1,
            "peer-limit-global": 20,
            "peer-limit-per-torrent": 5
        }
        network_state["bandwidth_mode"] = "minimal"
    
    elif connection_quality == "very_poor":
        # For very poor connections, be very conservative
        settings = {
            "alt-speed-enabled": True,
            "alt-speed-down": 20,
            "alt-speed-up": 2,
            "download-queue-size": 1,
            "peer-limit-global": 30,
            "peer-limit-per-torrent": 10
        }
        network_state["bandwidth_mode"] = "minimal"
    
    elif connection_quality == "poor":
        # For poor connections, be conservative with bandwidth
        settings = {
            "alt-speed-enabled": True,
            "alt-speed-down": 50,
            "alt-speed-up": 5,
            "download-queue-size": 2,
            "peer-limit-global": 50,
            "peer-limit-per-torrent": 15
        }
        network_state["bandwidth_mode"] = "conservative"
    
    else:  # "good"
        # For good connections, use normal settings
        settings = {
            "alt-speed-enabled": False,
            "download-queue-size": 3,
            "peer-limit-global": 100,
            "peer-limit-per-torrent": 30
        }
        network_state["bandwidth_mode"] = "normal"
        
        # If we were previously offline, resume torrents
        if network_state["connection_quality"] == "offline":
            resume_all_torrents()
    
    # Apply settings to Transmission
    if settings:
        transmission_rpc_call("session-set", settings)
        logger.info(f"Adjusted settings for {connection_quality} connection")

def pause_all_torrents() -> None:
    """Pause all active torrents."""
    transmission_rpc_call("torrent-stop")
    logger.info("Paused all torrents due to network being offline")

def resume_all_torrents() -> None:
    """Resume all torrents."""
    transmission_rpc_call("torrent-start")
    logger.info("Resumed torrents after network reconnection")

def get_torrent_list() -> List[Dict]:
    """Get list of all torrents with their status."""
    response = transmission_rpc_call("torrent-get", {
        "fields": ["id", "name", "status", "downloadDir", "percentDone", "rateDownload", "rateUpload"]
    })
    
    if response and "arguments" in response and "torrents" in response["arguments"]:
        return response["arguments"]["torrents"]
    return []

def main() -> None:
    """Main loop for the connection manager."""
    logger.info("Starting Tactical BitTorrent Connection Manager")
    
    # Wait for Transmission to be fully up
    time.sleep(10)
    
    while True:
        try:
            # Check basic connectivity
            is_online = check_network_connectivity()
            
            if is_online:
                # If we're online, measure connection quality
                connection_quality = measure_connection_quality()
                network_state["is_online"] = True
                network_state["last_online"] = time.time()
                network_state["connection_quality"] = connection_quality
                network_state["reconnect_count"] = 0
                
                logger.info(f"Network status: {connection_quality}")
                
                # Adjust transmission settings based on connection quality
                adjust_transmission_settings(connection_quality)
                
                # Log current torrents status
                torrents = get_torrent_list()
                active_downloads = sum(1 for t in torrents if t.get("rateDownload", 0) > 0)
                active_uploads = sum(1 for t in torrents if t.get("rateUpload", 0) > 0)
                logger.info(f"Active torrents: {len(torrents)} ({active_downloads} downloading, {active_uploads} uploading)")
                
            else:
                # We're offline
                network_state["is_online"] = False
                network_state["connection_quality"] = "offline"
                network_state["reconnect_count"] += 1
                
                logger.warning(f"Network is offline (attempt {network_state['reconnect_count']})")
                
                # Adjust transmission settings for offline mode
                adjust_transmission_settings("offline")
            
        except Exception as e:
            logger.error(f"Error in connection manager: {e}")
        
        # Sleep before next check
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
