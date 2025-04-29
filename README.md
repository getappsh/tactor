# Tactical BitTorrent Stack Deployment Guide

This guide will help you deploy a complete BitTorrent stack optimized for tactical networks with low bandwidth and frequent disconnections.

## Components

1. **Aquatic UDP Tracker**: High-performance BitTorrent tracker written in Rust
2. **Transmission BitTorrent Client**: Lightweight client with good disconnection resilience
3. **Connection Manager**: Monitors network status and adjusts settings dynamically

## Directory Structure

Create the following directory structure:
```
tactical-bittorrent/
├── aquatic_udp.Dockerfile
├── connection-manager.Dockerfile
├── connection_manager.py
├── docker-compose.yml
├── requirements.txt
├── transmission-settings.json
├── transmission/
│   ├── config/       # Will be created automatically
│   ├── downloads/    # Will be created automatically
│   └── watch/        # Will be created automatically
```

## Deployment Steps

### 1. Create All Required Files

Save all the files provided above to their respective locations.

### 2. Prepare Your Environment

```bash
# Create necessary directories
mkdir -p tactical-bittorrent/transmission/{config,downloads,watch}
cd tactical-bittorrent
```

### 3. Deploy with Docker Compose

```bash
# Start all services
docker-compose up -d

# Check logs to verify everything is running
docker-compose logs -f
```

## Usage

### Access the Transmission Web UI

Open a web browser and navigate to:
```
http://<your-server-ip>:9091
```

Login with:
- Username: `admin`
- Password: `tactical_pass`

### Add Torrents

1. **Web UI**: Upload .torrent files through the Transmission web interface
2. **Watch Directory**: Place .torrent files in the `./transmission/watch` directory
3. **Magnet Links**: Paste magnet links in the Transmission web UI

### Custom Trackers

When creating .torrent files for your tactical network, add your Aquatic UDP tracker:
```
udp://<your-server-ip>:3000/announce
```

## Optimizing for Your Environment

### Low Bandwidth Settings

The configuration is already optimized for low bandwidth, but you can further adjust:

1. Edit `transmission-settings.json`:
   - Reduce `alt-speed-down` and `alt-speed-up` values
   - Decrease `peer-limit-global` and `peer-limit-per-torrent`

2. Update the Docker Compose environment variables:
   ```yaml
   environment:
     - TRANSMISSION_ALT_SPEED_DOWN=30  # Even lower limit (KB/s)
     - TRANSMISSION_ALT_SPEED_UP=5     # Even lower limit (KB/s)
   ```

### Handling Disconnections

The Connection Manager will automatically:
- Pause torrents when connectivity is lost
- Resume them when connectivity returns
- Adjust bandwidth settings based on connection quality

## Troubleshooting

### Tracker Issues

If peers can't connect to the tracker:
1. Check the Aquatic tracker logs: `docker logs aquatic-tracker`
2. Verify UDP port 3000 is accessible (not blocked by firewalls)
3. Try running with `--network="host"` for better connectivity

### Client Issues

If Transmission has problems:
1. Check Transmission logs: `docker logs transmission`
2. Verify if the Connection Manager is properly adjusting settings
3. Manually modify settings through the web UI if needed

## Security Considerations

This deployment is focused on functionality in tactical environments. If security is a concern:

1. Change the default username/password in `transmission-settings.json`
2. Set up the RPC whitelist to limit access to specific IPs
3. Consider setting up a VPN or SSH tunnel for accessing the web UI
