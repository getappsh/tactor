# syntax=docker/dockerfile:1
# aquatic_udp - fixed version
FROM rust:latest AS builder

# Install required dependencies
RUN apt-get update && apt-get install -y git

# Clone the repository directly instead of copying local files
WORKDIR /usr/src
RUN git clone https://github.com/greatest-ape/aquatic.git
WORKDIR /usr/src/aquatic

# Build aquatic_udp
RUN cargo build --release -p aquatic_udp

# Create the final image
FROM debian:stable-slim

# Install required runtime dependencies
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

ENV CONFIG_FILE_CONTENTS "log_level = 'warn'"
ENV ACCESS_LIST_CONTENTS ""

WORKDIR /root/

# Copy only the compiled binary from the builder stage
COPY --from=builder /usr/src/aquatic/target/release/aquatic_udp ./

# Create entry point script for setting config and access list file contents at runtime
RUN echo '#!/bin/bash\necho -e "$CONFIG_FILE_CONTENTS" > ./config.toml\necho -e "$ACCESS_LIST_CONTENTS" > ./access-list.txt\nexec ./aquatic_udp -c ./config.toml "$@"' > ./entrypoint.sh && \
    chmod +x ./entrypoint.sh

# Expose UDP port for tracker
EXPOSE 3000/udp

ENTRYPOINT ["./entrypoint.sh"]
