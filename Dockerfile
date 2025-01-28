FROM python:3.12.6

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install Redis server and supervisord
RUN apt-get update && apt-get install -y \
redis-server \
supervisor \
&& rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Make the run script executable
RUN chmod +x docker_run_server.sh

# Copy the supervisord configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose port 80
EXPOSE 80

# Start the server
ENTRYPOINT ["./docker_run_server.sh"]
