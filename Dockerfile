FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-setuptools \
    bpfcc-tools \
    python3-bpfcc \
    clang llvm libelf-dev libbpfcc-dev build-essential \
    ca-certificates curl \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["python3", "ebpf_tracker.py", "--web"]