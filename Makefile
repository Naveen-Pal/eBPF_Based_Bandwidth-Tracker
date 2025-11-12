.PHONY: help install run run-web cli clean deps check

help:
	@echo "eBPF Bandwidth Tracker - Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  make install    - Install all dependencies"
	@echo "  make run        - Run tracker (CLI mode)"
	@echo "  make run-web    - Run tracker with web UI"
	@echo "  make clean      - Clean up temporary files"
	@echo "  make deps       - Install Python dependencies"
	@echo "  make check      - Check system requirements"

install:
	@echo "Installing eBPF Bandwidth Tracker..."
	@sudo bash install.sh

deps:
	@echo "Installing Python dependencies..."
	@pip3 install -r requirements.txt
	@pip3 install tabulate

run:
	@echo "Starting bandwidth tracker (CLI mode)..."
	@sudo ./venv/bin/python3 ebpf_tracker.py --interval 5

run-web:
	@echo "Starting bandwidth tracker with web UI..."
	@echo "Access at: http://localhost:8080"
	@sudo ./venv/bin/python3 ebpf_tracker.py --web

check:
	@echo "Checking system requirements..."
	@echo "Kernel version: $$(uname -r)"
	@python3 -c "import bcc; print('BCC version:', bcc.__version__)" 2>/dev/null || echo "BCC not installed"
	@python3 -c "import flask; print('Flask version:', flask.__version__)"
	@echo "eBPF support: $$(grep CONFIG_BPF /boot/config-$$(uname -r) 2>/dev/null || echo 'Unknown')"

clean:
	@echo "Cleaning up..."
	@sudo rm -f *.pyc
	@sudo rm -rf __pycache__
	@sudo rm -rf venv
	@sudo rm -f test_bandwidth.db
	@sudo rm -f *.log
	@echo "Done"

service-install:
	@echo "Installing systemd service..."
	@sudo cp ebpf-bandwidth-tracker.service /etc/systemd/system/
	@sudo systemctl daemon-reload
	@echo "Service installed. Enable with: sudo systemctl enable ebpf-bandwidth-tracker"

service-start:
	@sudo systemctl start ebpf-bandwidth-tracker

service-stop:
	@sudo systemctl stop ebpf-bandwidth-tracker

service-status:
	@sudo systemctl status ebpf-bandwidth-tracker

service-logs:
	@sudo journalctl -u ebpf-bandwidth-tracker -f

db-query:
	@sqlite3 bandwidth.db "SELECT process_name, SUM(tx_bytes) as tx, SUM(rx_bytes) as rx FROM bandwidth_records GROUP BY process_name ORDER BY (tx+rx) DESC LIMIT 10;"

db-clean:
	@sudo ./venv/bin/python3 cli.py --cleanup 7

db-backup:
	@cp bandwidth.db bandwidth_backup_$$(date +%Y%m%d_%H%M%S).db
	@echo "Database backed up"
