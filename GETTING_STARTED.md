# Getting Started Checklist

Welcome to the eBPF Bandwidth Tracker project! Follow this checklist to get up and running.

## ☑️ Pre-Installation Checklist

- [ ] **Linux System**: Ensure you're running Linux (Ubuntu 20.04+, Debian 11+, Fedora 35+, or similar)
- [ ] **Kernel Version**: Check kernel version is 4.15 or higher
  ```bash
  uname -r
  ```
- [ ] **Root Access**: Verify you have sudo/root privileges
  ```bash
  sudo -v
  ```
- [ ] **Internet Connection**: Required for downloading dependencies

## ☑️ Installation Steps

### Option 1: Automated Installation (Recommended)

- [ ] **Run Installation Script**
  ```bash
  cd /home/moba/Documents/courseprep/CN/project
  sudo bash install.sh
  ```

- [ ] **Verify Installation**
  ```bash
  python3 -c "import bcc; print('BCC installed:', bcc.__version__)"
  python3 -c "import flask; print('Flask installed:', flask.__version__)"
  ```

### Option 2: Manual Installation

- [ ] **Install System Dependencies** (Ubuntu/Debian)
  ```bash
  sudo apt-get update
  sudo apt-get install -y \
    build-essential \
    linux-headers-$(uname -r) \
    bpfcc-tools \
    python3-bpfcc \
    python3-pip \
    sqlite3
  ```

- [ ] **Install Python Dependencies**
  ```bash
  pip3 install -r requirements.txt
  pip3 install tabulate
  ```

- [ ] **Make Scripts Executable**
  ```bash
  chmod +x *.py *.sh
  ```

## ☑️ First Run

### Quick Test

- [ ] **Start the Quick Start Wizard**
  ```bash
  sudo ./quickstart.sh
  ```

- [ ] **Select Option 1** (Web UI) or **Option 2** (CLI)

### Manual Start

- [ ] **Start with Web UI**
  ```bash
  sudo python3 ebpf_tracker.py --web
  ```

- [ ] **Open Browser**
  - Navigate to: http://localhost:8080
  
- [ ] **Verify Data Collection**
  - Generate some network traffic (open websites, download files)
  - Refresh the dashboard
  - You should see processes appearing

## ☑️ Basic Usage

- [ ] **Try CLI Commands**
  ```bash
  # View live monitoring
  sudo python3 cli.py --live
  
  # View top 10 processes
  sudo python3 cli.py --top 10
  
  # View protocol breakdown
  sudo python3 cli.py --protocol-breakdown
  ```

- [ ] **Explore Web Interface**
  - Click through all tabs: Real-time, History, Protocols, Remote IPs, Charts
  - Try filtering processes
  - Adjust time windows

- [ ] **Check Database**
  ```bash
  sqlite3 bandwidth.db "SELECT COUNT(*) FROM bandwidth_records;"
  ```

## ☑️ Testing

- [ ] **Generate Test Traffic**
  ```bash
  # Download a file
  wget https://www.google.com/robots.txt
  
  # Ping test
  ping -c 50 8.8.8.8
  
  # DNS queries
  for i in {1..20}; do nslookup google.com; done
  ```

- [ ] **Verify Traffic is Tracked**
  - Check web UI for wget/ping processes
  - Run: `sudo python3 cli.py --top 10`
  - Should see your test processes

## ☑️ Configuration

- [ ] **Review Configuration Options**
  ```bash
  python3 ebpf_tracker.py --help
  python3 cli.py --help
  ```

- [ ] **Customize Update Interval** (optional)
  ```bash
  sudo python3 ebpf_tracker.py --interval 2
  ```

- [ ] **Use Custom Database Path** (optional)
  ```bash
  sudo python3 ebpf_tracker.py --db /path/to/custom.db
  ```

## ☑️ Production Setup (Optional)

- [ ] **Install as System Service**
  ```bash
  sudo cp ebpf-bandwidth-tracker.service /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo systemctl enable ebpf-bandwidth-tracker
  sudo systemctl start ebpf-bandwidth-tracker
  ```

- [ ] **Verify Service is Running**
  ```bash
  sudo systemctl status ebpf-bandwidth-tracker
  ```

- [ ] **Check Service Logs**
  ```bash
  sudo journalctl -u ebpf-bandwidth-tracker -f
  ```

## ☑️ Troubleshooting

If you encounter issues, check these:

- [ ] **BCC Installation**
  ```bash
  python3 -c "import bcc; print('OK')"
  ```

- [ ] **Kernel Support**
  ```bash
  grep CONFIG_BPF /boot/config-$(uname -r)
  ```

- [ ] **Permissions**
  - Ensure running with sudo
  - Check: `sudo -v`

- [ ] **Kernel Functions Available**
  ```bash
  grep tcp_sendmsg /proc/kallsyms
  grep tcp_recvmsg /proc/kallsyms
  ```

- [ ] **Check System Logs**
  ```bash
  sudo dmesg | grep -i bpf
  sudo journalctl -xe
  ```

## ☑️ Learning Resources

- [ ] **Read Documentation**
  - [x] README.md - Overview and quick start
  - [ ] DEVELOPMENT.md - Architecture and development
  - [ ] TESTING.md - Testing procedures
  - [ ] PROJECT_SUMMARY.md - Complete project overview

- [ ] **Run Examples**
  ```bash
  python3 examples.py
  ```

- [ ] **Run Tests**
  ```bash
  python3 test_storage.py
  ```

## ☑️ Next Steps

After successful setup:

- [ ] **Monitor Your System**
  - Let it run for a few hours
  - Analyze bandwidth patterns
  - Identify bandwidth-heavy processes

- [ ] **Explore Historical Data**
  ```bash
  sudo python3 cli.py --history --hours 24
  ```

- [ ] **Try Advanced Queries**
  - Check examples.py for programmatic usage
  - Write custom SQL queries

- [ ] **Customize for Your Needs**
  - Modify update intervals
  - Add custom metrics
  - Extend protocol support

- [ ] **Deploy to Production** (if needed)
  - Set up as systemd service
  - Configure log rotation
  - Set up monitoring/alerts

## 🎉 Success Criteria

You've successfully set up the project when:

✅ eBPF program loads without errors
✅ Web UI is accessible at http://localhost:8080
✅ CLI shows real-time bandwidth data
✅ Database contains bandwidth records
✅ Processes appear in the dashboard
✅ Charts render with time-series data

## 📞 Getting Help

If you're stuck:

1. **Check Documentation**: Read README.md and TESTING.md
2. **Review Logs**: `sudo journalctl -xe`
3. **System Check**: `sudo ./quickstart.sh` → Option 4
4. **Common Issues**: See TROUBLESHOOTING section in README.md

## 🚀 Quick Commands Reference

```bash
# Start with Web UI
sudo python3 ebpf_tracker.py --web

# Live CLI monitoring
sudo python3 cli.py --live

# Top 10 processes (last hour)
sudo python3 cli.py --top 10 --hours 1

# Protocol breakdown
sudo python3 cli.py --protocol-breakdown

# IP breakdown
sudo python3 cli.py --ip-breakdown

# Historical data (24 hours)
sudo python3 cli.py --history --hours 24

# Clean old data (7 days)
sudo python3 cli.py --cleanup 7

# Run examples
python3 examples.py

# Run tests
python3 test_storage.py
```

## 📋 Final Checklist

- [ ] Installation completed successfully
- [ ] First run successful (Web UI or CLI)
- [ ] Data is being collected
- [ ] Can view bandwidth statistics
- [ ] Understand basic commands
- [ ] Know where to find help

**Congratulations! You're ready to use the eBPF Bandwidth Tracker! 🎉**

---

**Need help?** Check the documentation files or run the system check:
```bash
sudo ./quickstart.sh  # Then select Option 4
```
