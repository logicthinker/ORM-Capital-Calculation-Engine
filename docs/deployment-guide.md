# Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the ORM Capital Calculator Engine in different environments: local development, staging, and production. Each environment has specific requirements and configurations optimized for its use case.

## Table of Contents

1. [Local Development Deployment](#local-development-deployment)
2. [Staging Environment Deployment](#staging-environment-deployment)
3. [Production Environment Deployment](#production-environment-deployment)
4. [Container Deployment](#container-deployment)
5. [Kubernetes Deployment](#kubernetes-deployment)
6. [Cloud Provider Specific Guides](#cloud-provider-specific-guides)
7. [Troubleshooting](#troubleshooting)

## Local Development Deployment

### Prerequisites

- Python 3.9 or higher
- Git
- SQLite (included with Python)
- Optional: Docker and Docker Compose

### Step 1: Clone Repository

```bash
git clone https://github.com/your-org/orm-capital-calculator.git
cd orm-capital-calculator
```

### Step 2: Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -e .[dev,test]
```

### Step 3: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your settings
# Key settings for development:
ENVIRONMENT=development
DATABASE_URL=sqlite:///./data/orm_calculator.db
LOG_LEVEL=DEBUG
```

### Step 4: Initialize Database

```bash
# Create data directory
mkdir -p data

# Run database initialization
python scripts/init-database.py

# Run migrations
alembic upgrade head
```

### Step 5: Start Development Server

```bash
# Start the server
python -m uvicorn orm_calculator.main:create_application --host 127.0.0.1 --port 8000 --reload

# Or use the convenience script
python scripts/start-server.py
```

### Step 6: Verify Installation

```bash
# Test health endpoint
curl http://localhost:8000/api/v1/health

# View API documentation
# Open browser to: http://localhost:8000/docs
```

### Development with Docker

```bash
# Build and start development environment
docker-compose up orm-calculator-dev

# Or build manually
docker build --target development-base -t orm-calculator:dev .
docker run -p 8000:8000 -v $(pwd):/app orm-calculator:dev
```

## Staging Environment Deployment

### Prerequisites

- Linux server (Ubuntu 20.04+ recommended)
- PostgreSQL 13+
- Redis 6+
- Nginx
- SSL certificates
- Python 3.9+

### Step 1: Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3.9 python3.9-venv python3-pip postgresql-client redis-tools nginx git

# Create application user
sudo useradd -m -s /bin/bash orm-calculator
sudo usermod -aG sudo orm-calculator
```

### Step 2: Database Setup

```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Create database and user
CREATE DATABASE orm_calculator_staging;
CREATE USER orm_user WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE orm_calculator_staging TO orm_user;
\q

# Test connection
psql -h localhost -U orm_user -d orm_calculator_staging
```

### Step 3: Application Deployment

```bash
# Switch to application user
sudo su - orm-calculator

# Clone repository
git clone https://github.com/your-org/orm-capital-calculator.git
cd orm-capital-calculator

# Create virtual environment
python3.9 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e .[production,cache]

# Configure environment
cp deployment/templates/.env.staging .env
# Edit .env with staging-specific settings

# Run database migrations
alembic upgrade head

# Create systemd service
sudo cp deployment/systemd/orm-calculator.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable orm-calculator
sudo systemctl start orm-calculator
```

### Step 4: Nginx Configuration

```bash
# Copy Nginx configuration
sudo cp deployment/nginx/staging.conf /etc/nginx/sites-available/orm-calculator
sudo ln -s /etc/nginx/sites-available/orm-calculator /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

### Step 5: SSL Certificate Setup

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d staging.orm-calculator.your-domain.com

# Test auto-renewal
sudo certbot renew --dry-run
```

### Step 6: Monitoring Setup

```bash
# Install monitoring tools
sudo apt install prometheus-node-exporter

# Configure log rotation
sudo cp deployment/logrotate/orm-calculator /etc/logrotate.d/

# Set up health check monitoring
sudo cp deployment/monitoring/health-check.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/health-check.sh

# Add to crontab
echo "*/5 * * * * /usr/local/bin/health-check.sh" | sudo crontab -
```

## Production Environment Deployment

### Prerequisites

- High-availability Linux servers
- PostgreSQL cluster with replication
- Redis cluster
- Load balancer (HAProxy/Nginx)
- SSL certificates from trusted CA
- Monitoring infrastructure
- Backup systems

### Step 1: Infrastructure Setup

#### Database Cluster

```bash
# Primary PostgreSQL server
sudo apt install postgresql-13 postgresql-contrib

# Configure PostgreSQL for production
sudo nano /etc/postgresql/13/main/postgresql.conf
# Key settings:
# max_connections = 200
# shared_buffers = 256MB
# effective_cache_size = 1GB
# maintenance_work_mem = 64MB

# Configure replication
sudo nano /etc/postgresql/13/main/pg_hba.conf
# Add replication entries

# Create replication user
sudo -u postgres createuser --replication -P replicator

# Set up standby servers
# (Detailed replication setup steps...)
```

#### Redis Cluster

```bash
# Install Redis
sudo apt install redis-server

# Configure Redis cluster
sudo nano /etc/redis/redis.conf
# Key settings:
# bind 0.0.0.0
# cluster-enabled yes
# cluster-config-file nodes.conf
# cluster-node-timeout 5000

# Start Redis cluster
redis-cli --cluster create \
  192.168.1.10:6379 192.168.1.11:6379 192.168.1.12:6379 \
  192.168.1.13:6379 192.168.1.14:6379 192.168.1.15:6379 \
  --cluster-replicas 1
```

### Step 2: Application Deployment

#### Multi-Server Setup

```bash
# On each application server
sudo useradd -m -s /bin/bash orm-calculator

# Deploy application
sudo su - orm-calculator
git clone https://github.com/your-org/orm-capital-calculator.git
cd orm-capital-calculator

# Set up environment
python3.9 -m venv venv
source venv/bin/activate
pip install -e .[production,cache]

# Configure for production
cp deployment/templates/.env.production .env
# Edit with production settings

# Run migrations (on one server only)
alembic upgrade head

# Create systemd service
sudo cp deployment/systemd/orm-calculator-prod.service /etc/systemd/system/orm-calculator.service
sudo systemctl daemon-reload
sudo systemctl enable orm-calculator
sudo systemctl start orm-calculator
```

#### Load Balancer Configuration

```bash
# HAProxy configuration
sudo nano /etc/haproxy/haproxy.cfg

# Add backend configuration:
backend orm-calculator
    balance roundrobin
    option httpchk GET /api/v1/health
    server app1 192.168.1.20:8000 check
    server app2 192.168.1.21:8000 check
    server app3 192.168.1.22:8000 check

frontend orm-calculator-frontend
    bind *:80
    bind *:443 ssl crt /etc/ssl/certs/orm-calculator.pem
    redirect scheme https if !{ ssl_fc }
    default_backend orm-calculator
```

### Step 3: Security Hardening

```bash
# Firewall configuration
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow from 192.168.1.0/24 to any port 5432  # Database
sudo ufw allow from 192.168.1.0/24 to any port 6379  # Redis

# Fail2ban setup
sudo apt install fail2ban
sudo cp deployment/fail2ban/orm-calculator.conf /etc/fail2ban/jail.d/
sudo systemctl restart fail2ban

# Log monitoring
sudo apt install logwatch
sudo cp deployment/logwatch/orm-calculator.conf /etc/logwatch/conf/services/
```

### Step 4: Backup Configuration

```bash
# Database backup script
sudo cp deployment/backup/db-backup.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/db-backup.sh

# Application backup script
sudo cp deployment/backup/app-backup.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/app-backup.sh

# Schedule backups
sudo crontab -e
# Add:
# 0 2 * * * /usr/local/bin/db-backup.sh
# 0 3 * * * /usr/local/bin/app-backup.sh
```

### Step 5: Monitoring and Alerting

```bash
# Prometheus setup
sudo useradd --no-create-home --shell /bin/false prometheus
sudo mkdir /etc/prometheus /var/lib/prometheus
sudo chown prometheus:prometheus /etc/prometheus /var/lib/prometheus

# Install Prometheus
wget https://github.com/prometheus/prometheus/releases/download/v2.40.0/prometheus-2.40.0.linux-amd64.tar.gz
tar xvf prometheus-2.40.0.linux-amd64.tar.gz
sudo cp prometheus-2.40.0.linux-amd64/prometheus /usr/local/bin/
sudo cp prometheus-2.40.0.linux-amd64/promtool /usr/local/bin/
sudo chown prometheus:prometheus /usr/local/bin/prometheus /usr/local/bin/promtool

# Configure Prometheus
sudo cp deployment/monitoring/prometheus.yml /etc/prometheus/
sudo cp deployment/systemd/prometheus.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable prometheus
sudo systemctl start prometheus

# Grafana setup
sudo apt-get install -y software-properties-common
sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
sudo apt-get update
sudo apt-get install grafana
sudo systemctl enable grafana-server
sudo systemctl start grafana-server
```

## Container Deployment

### Docker Deployment

#### Single Container

```bash
# Build production image
docker build --target production -t orm-calculator:prod .

# Run container
docker run -d \
  --name orm-calculator-prod \
  -p 8000:8000 \
  -v /data/orm-calculator:/app/data \
  -v /logs/orm-calculator:/app/logs \
  --env-file .env.production \
  --restart unless-stopped \
  orm-calculator:prod
```

#### Docker Compose Production

```bash
# Use production compose file
docker-compose -f docker-compose.prod.yml up -d

# Scale application
docker-compose -f docker-compose.prod.yml up -d --scale orm-calculator-prod=3

# View logs
docker-compose -f docker-compose.prod.yml logs -f orm-calculator-prod
```

### Container Health Checks

```bash
# Check container health
docker ps
docker inspect orm-calculator-prod | grep Health

# Manual health check
docker exec orm-calculator-prod curl -f http://localhost:8000/api/v1/health
```

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (1.20+)
- kubectl configured
- Helm 3.x (optional)
- Ingress controller
- Cert-manager for SSL

### Step 1: Prepare Kubernetes Resources

```bash
# Create namespace
kubectl create namespace orm-calculator

# Create secrets
kubectl create secret generic orm-calculator-secrets \
  --from-env-file=.env.production \
  -n orm-calculator

# Create TLS secret
kubectl create secret tls orm-calculator-tls \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key \
  -n orm-calculator
```

### Step 2: Deploy Application

```bash
# Apply Kubernetes manifests
kubectl apply -f deployment/kubernetes/

# Check deployment status
kubectl get pods -n orm-calculator
kubectl get services -n orm-calculator
kubectl get ingress -n orm-calculator

# View logs
kubectl logs -f deployment/orm-calculator-app -n orm-calculator
```

### Step 3: Configure Ingress

```bash
# Install ingress controller (if not already installed)
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.5.1/deploy/static/provider/cloud/deploy.yaml

# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.10.0/cert-manager.yaml

# Create cluster issuer
kubectl apply -f deployment/kubernetes/cluster-issuer.yaml
```

### Step 4: Monitoring Setup

```bash
# Install Prometheus Operator
kubectl apply -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/main/bundle.yaml

# Apply ServiceMonitor
kubectl apply -f deployment/kubernetes/service-monitor.yaml

# Install Grafana
kubectl apply -f deployment/kubernetes/grafana.yaml
```

### Helm Deployment (Alternative)

```bash
# Add Helm repository
helm repo add orm-calculator https://charts.orm-calculator.com
helm repo update

# Install with Helm
helm install orm-calculator orm-calculator/orm-calculator \
  --namespace orm-calculator \
  --create-namespace \
  --values deployment/helm/values-production.yaml

# Upgrade deployment
helm upgrade orm-calculator orm-calculator/orm-calculator \
  --namespace orm-calculator \
  --values deployment/helm/values-production.yaml
```

## Cloud Provider Specific Guides

### AWS Deployment

#### ECS Deployment

```bash
# Create ECS cluster
aws ecs create-cluster --cluster-name orm-calculator-prod

# Create task definition
aws ecs register-task-definition --cli-input-json file://deployment/aws/task-definition.json

# Create service
aws ecs create-service \
  --cluster orm-calculator-prod \
  --service-name orm-calculator \
  --task-definition orm-calculator:1 \
  --desired-count 3 \
  --load-balancers targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=orm-calculator,containerPort=8000
```

#### EKS Deployment

```bash
# Create EKS cluster
eksctl create cluster --name orm-calculator-prod --region ap-south-1

# Configure kubectl
aws eks update-kubeconfig --region ap-south-1 --name orm-calculator-prod

# Deploy application
kubectl apply -f deployment/kubernetes/
```

### Azure Deployment

#### Container Instances

```bash
# Create resource group
az group create --name orm-calculator-rg --location centralindia

# Create container instance
az container create \
  --resource-group orm-calculator-rg \
  --name orm-calculator \
  --image orm-calculator:prod \
  --cpu 2 \
  --memory 4 \
  --ports 8000 \
  --environment-variables ENVIRONMENT=production
```

#### AKS Deployment

```bash
# Create AKS cluster
az aks create \
  --resource-group orm-calculator-rg \
  --name orm-calculator-aks \
  --node-count 3 \
  --location centralindia

# Get credentials
az aks get-credentials --resource-group orm-calculator-rg --name orm-calculator-aks

# Deploy application
kubectl apply -f deployment/kubernetes/
```

### Google Cloud Deployment

#### Cloud Run

```bash
# Build and push image
gcloud builds submit --tag gcr.io/PROJECT_ID/orm-calculator

# Deploy to Cloud Run
gcloud run deploy orm-calculator \
  --image gcr.io/PROJECT_ID/orm-calculator \
  --platform managed \
  --region asia-south1 \
  --allow-unauthenticated
```

#### GKE Deployment

```bash
# Create GKE cluster
gcloud container clusters create orm-calculator-cluster \
  --zone asia-south1-a \
  --num-nodes 3

# Get credentials
gcloud container clusters get-credentials orm-calculator-cluster --zone asia-south1-a

# Deploy application
kubectl apply -f deployment/kubernetes/
```

## Troubleshooting

### Common Issues

#### Database Connection Issues

```bash
# Check database connectivity
psql -h DATABASE_HOST -U DATABASE_USER -d DATABASE_NAME

# Check connection pool
kubectl exec -it deployment/orm-calculator-app -- python -c "
from orm_calculator.database import get_db_session
import asyncio
async def test():
    async with get_db_session() as session:
        result = await session.execute('SELECT 1')
        print('Database connection successful')
asyncio.run(test())
"
```

#### Performance Issues

```bash
# Check resource usage
kubectl top pods -n orm-calculator
kubectl describe pod POD_NAME -n orm-calculator

# Check application metrics
curl http://localhost:8000/api/v1/performance/metrics

# Check database performance
psql -h DATABASE_HOST -U DATABASE_USER -d DATABASE_NAME -c "
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;
"
```

#### SSL/TLS Issues

```bash
# Check certificate validity
openssl x509 -in /path/to/cert.pem -text -noout

# Test SSL connection
openssl s_client -connect orm-calculator.your-domain.com:443

# Check cert-manager status (Kubernetes)
kubectl get certificates -n orm-calculator
kubectl describe certificate orm-calculator-tls -n orm-calculator
```

#### Application Startup Issues

```bash
# Check application logs
kubectl logs -f deployment/orm-calculator-app -n orm-calculator

# Check configuration
kubectl exec -it deployment/orm-calculator-app -- env | grep -E "(DATABASE|REDIS|JWT)"

# Test health endpoint
kubectl exec -it deployment/orm-calculator-app -- curl http://localhost:8000/api/v1/health
```

### Log Analysis

```bash
# Application logs
tail -f /var/log/orm-calculator/app.log

# Database logs
sudo tail -f /var/log/postgresql/postgresql-13-main.log

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# System logs
journalctl -u orm-calculator -f
```

### Performance Tuning

```bash
# Database tuning
sudo nano /etc/postgresql/13/main/postgresql.conf
# Adjust based on server resources

# Application tuning
# Adjust worker processes in gunicorn configuration
# Tune connection pool sizes
# Configure cache TTL values

# System tuning
# Adjust file descriptor limits
# Configure kernel parameters
# Optimize network settings
```

### Backup and Recovery Testing

```bash
# Test database backup
pg_dump -h DATABASE_HOST -U DATABASE_USER DATABASE_NAME > backup_test.sql

# Test database restore
createdb test_restore
psql -h DATABASE_HOST -U DATABASE_USER test_restore < backup_test.sql

# Test application backup
tar -czf app_backup_test.tar.gz /opt/orm-calculator/

# Test disaster recovery
# Follow disaster recovery procedures
# Verify RTO/RPO targets
```

## Support and Maintenance

### Regular Maintenance Tasks

1. **Daily**
   - Check system health
   - Review error logs
   - Monitor performance metrics

2. **Weekly**
   - Update security patches
   - Review backup integrity
   - Analyze performance trends

3. **Monthly**
   - Test disaster recovery procedures
   - Review and update documentation
   - Capacity planning review

4. **Quarterly**
   - Security audit
   - Performance optimization
   - Dependency updates

### Emergency Procedures

1. **System Down**
   - Check load balancer status
   - Verify database connectivity
   - Review application logs
   - Escalate to on-call team

2. **Performance Degradation**
   - Check resource utilization
   - Review slow queries
   - Scale application if needed
   - Investigate root cause

3. **Security Incident**
   - Isolate affected systems
   - Preserve evidence
   - Follow incident response plan
   - Notify stakeholders

For additional support, contact:
- **Technical Support**: support@your-company.com
- **Emergency Hotline**: +91-XXX-XXX-XXXX
- **Documentation**: https://docs.orm-calculator.your-domain.com