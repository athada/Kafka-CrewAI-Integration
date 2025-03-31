FROM python:3.11-slim-buster

WORKDIR /app

# Install necessary build tools and dependencies for compiling SQLite3
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    tar \
    libreadline-dev \
    libsqlite3-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Set SQLite version (ensure it's >= 3.35.0)
ENV SQLITE_VERSION=3400000
ENV SQLITE_DIR=/usr/local/sqlite3

# Download, compile, and install SQLite3
RUN wget https://www.sqlite.org/2022/sqlite-autoconf-${SQLITE_VERSION}.tar.gz && \
    tar xvf sqlite-autoconf-${SQLITE_VERSION}.tar.gz && \
    cd sqlite-autoconf-${SQLITE_VERSION} && \
    ./configure --prefix=${SQLITE_DIR} && \
    make -j$(nproc) && make install && \
    cd .. && rm -rf sqlite-autoconf-${SQLITE_VERSION}*

# Set environment variables to use the new SQLite3
ENV PATH="${SQLITE_DIR}/bin:${PATH}"
ENV LD_LIBRARY_PATH="${SQLITE_DIR}/lib:${LD_LIBRARY_PATH}"
ENV PKG_CONFIG_PATH="${SQLITE_DIR}/lib/pkgconfig:${PKG_CONFIG_PATH}"

# Verify the correct SQLite version is used
RUN sqlite3 --version

# Upgrade pip and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project files
COPY . .

# Run the application
CMD ["python", "crew.py"]
