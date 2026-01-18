# AWS Deployment Setup Guide

This guide will walk you through setting up AWS for deploying Claire to EC2.

## Prerequisites
- AWS account
- Basic familiarity with AWS Console

---

## Step 1: Create IAM User for GitHub Actions

This user will be used by GitHub Actions to push images to ECR.

1. Go to **IAM Console** → **Users** → **Create user**
2. Username: `claire-github-actions`
3. Click **Next**
4. Select **Attach policies directly**
5. Click **Create policy**
6. Switch to **JSON** tab and paste:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "ecr:PutImage",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload",
                "ecr:CreateRepository",
                "ecr:DescribeRepositories",
                "sts:GetCallerIdentity"
            ],
            "Resource": "*"
        }
    ]
}
```

7. Name it: `ClaireECRAccess`
8. Click **Create policy**
9. Go back to user creation, refresh, and select `ClaireECRAccess`
10. Click **Next** → **Create user**
11. Click on the user → **Security credentials** tab
12. Click **Create access key**
13. Select **Application running outside AWS**
14. Click **Create access key**
15. **IMPORTANT**: Copy both:
    - **Access key ID** → Save as `AWS_ACCESS_KEY_ID` in GitHub Secrets
    - **Secret access key** → Save as `AWS_SECRET_ACCESS_KEY` in GitHub Secrets

---

## Step 2: Create ECR Repositories

ECR repositories will be created automatically by the GitHub Actions workflow, but you can create them manually:

1. Go to **ECR Console** → **Repositories** → **Create repository**
2. Repository name: `claire-api`
3. Visibility: **Private**
4. Click **Create repository**
5. Repeat for `claire-db`

**Note**: The workflow will create these automatically if they don't exist.

---

## Step 3: Launch EC2 Instance

1. Go to **EC2 Console** → **Instances** → **Launch instance**

### Basic Configuration:
- **Name**: `claire-production`
- **AMI**: Ubuntu Server 22.04 LTS (or latest)
- **Instance type**: `t3.medium` or larger (recommended: `t3.large`)
- **Key pair**: 
  - If you have one: Select it
  - If not: Click **Create new key pair**
    - Name: `claire-deploy-key`
    - Key pair type: **RSA**
    - Private key file format: **.pem**
    - Click **Create key pair**
    - **Download and save the .pem file securely**

### Network Settings:
- **VPC**: Default VPC (or your preferred VPC)
- **Subnet**: Any public subnet
- **Auto-assign Public IP**: **Enable**
- **Security group**: Click **Create security group**
  - Name: `claire-my`
  - Description: `Security group for Claire application`
  - **Inbound rules**:
    - SSH (22) from **My IP** (or 0.0.0.0/0 if you prefer)
    - Custom TCP (3000) from **0.0.0.0/0** (Frontend/Web)
    - Custom TCP (8000) from **0.0.0.0/0** (Backend API)
    - Custom TCP (9000) from **0.0.0.0/0** (MinIO API)
    - Custom TCP (9001) from **0.0.0.0/0** (MinIO Console)
  - Click **Create security group**

### Configure Storage:
- **Volume size**: At least 20 GB (30 GB recommended)

### Advanced Details:
- Scroll to **IAM instance profile**: Select **Create new IAM role** (we'll configure this next)

3. Click **Launch instance**

---

## Step 4: Create IAM Role for EC2 Instance

This allows EC2 to pull images from ECR without storing credentials.

1. Go to **IAM Console** → **Roles** → **Create role**
2. Trusted entity type: **AWS service**
3. Use case: **EC2**
4. Click **Next**
5. Search for and select: **AmazonEC2ContainerRegistryReadOnly**
6. Click **Next**
7. Role name: `claire-ec2-role`
8. Click **Create role**

### Attach Role to EC2 Instance:

1. Go to **EC2 Console** → **Instances**
2. Select your instance → **Actions** → **Security** → **Modify IAM role**
3. Select `claire-ec2-role`
4. Click **Update IAM role**

---

## Step 5: Setup EC2 Instance

SSH into your EC2 instance:

```bash
chmod 600 claire-production.pem

# Replace with your key path and instance IP
ssh -i ~/path/to/claire-deploy-key.pem ubuntu@YOUR_EC2_IP
```

Once connected, run:

```bash
# Update system
sudo apt-get update

# Install Docker
sudo apt-get install -y docker.io

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
sudo apt install -y unzip
unzip awscliv2.zip
sudo ./aws/install
rm -rf aws awscliv2.zip

# Add user to docker group
sudo usermod -aG docker $USER

# Logout and login again, or run:
newgrp docker

# Verify installations
docker --version
docker-compose --version
aws --version

# Create project directory
mkdir -p ~/claire
cd ~/claire

# Create .env file (you'll need to copy your local .env content here)
nano .env
# Paste all your environment variables from your local .env file
# Make sure POSTGRES_HOST=db (not localhost)
# Make sure MINIO_ENDPOINT=minio:9000
# Add web environment variables:
# NEXT_PUBLIC_API_BASE_URL=http://YOUR_EC2_IP:8000
# NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key
# CLERK_SECRET_KEY=your_clerk_secret_key
ls -la
```

---

## Step 6: Configure GitHub Secrets

1. Go to your GitHub repository
2. **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**

Add these secrets:

| Secret Name | Value | Where to Find |
|------------|-------|---------------|
| `AWS_ACCESS_KEY_ID` | From Step 1 | IAM User access key |
| `AWS_SECRET_ACCESS_KEY` | From Step 1 | IAM User secret key |
| `EC2_HOST` | Your EC2 public IP or hostname | EC2 Console → Instances → Public IPv4 address |
| `EC2_USER` | `ubuntu` (for Ubuntu) or `ec2-user` (for Amazon Linux) | Depends on your AMI |
| `EC2_SSH_PRIVATE_KEY` | Content of your .pem file | Open the .pem file and copy ALL content including `-----BEGIN RSA PRIVATE KEY-----` and `-----END RSA PRIVATE KEY-----` |

### Getting EC2_HOST:
- Go to **EC2 Console** → **Instances**
- Click on your instance
- Copy the **Public IPv4 address** (e.g., `54.123.45.67`)
- Or use the **Public IPv4 DNS** (e.g., `ec2-54-123-45-67.ap-southeast-5.compute.amazonaws.com`)

### Getting EC2_SSH_PRIVATE_KEY:
```bash
# On your local machine, run:
cat ~/path/to/claire-deploy-key.pem
# Copy the entire output including headers
```

---

## Step 7: Test the Deployment

1. Make a small change to your code
2. Commit and push to `main` branch:
   ```bash
   git add .
   git commit -m "Test deployment"
   git push origin main
   ```
3. Go to **GitHub** → **Actions** tab
4. Watch the workflow run
5. Once complete, check your EC2 instance:
   ```bash
   ssh -i ~/path/to/claire-deploy-key.pem ubuntu@YOUR_EC2_IP
   cd ~/claire
   docker compose -f docker-compose.aws.yaml ps
   ```
6. Access your application:
   - Frontend/Web: `http://YOUR_EC2_IP:3000`
   - Backend API: `http://YOUR_EC2_IP:8000/docs`
   - MinIO Console: `http://YOUR_EC2_IP:9001`

---

## Troubleshooting

### If deployment fails:

1. **Check GitHub Actions logs** for errors
2. **SSH into EC2** and check:
   ```bash
   cd ~/claire
   docker compose -f docker-compose.aws.yaml logs
   ```
3. **Verify ECR login**:
   ```bash
   aws ecr get-login-password --region ap-southeast-5 | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.ap-southeast-5.amazonaws.com
   ```
4. **Check IAM role** is attached to EC2 instance
5. **Verify security group** has correct ports open

### Common Issues:

- **Permission denied**: Make sure EC2 user is in docker group (`sudo usermod -aG docker $USER`)
- **ECR login failed**: Verify IAM role is attached to EC2
- **Port not accessible**: Check security group inbound rules
- **Container fails to start**: Check `.env` file has all required variables

---

## Security Best Practices

1. **Restrict SSH access**: In security group, only allow SSH from your IP
2. **Use HTTPS**: Consider setting up a reverse proxy (nginx) with SSL
3. **Rotate credentials**: Regularly rotate AWS access keys
4. **Monitor costs**: Set up billing alerts
5. **Backup data**: Regularly backup PostgreSQL volumes

---

## Next Steps

- Set up a domain name and point it to your EC2 IP
- Configure nginx as reverse proxy
- Set up SSL certificates (Let's Encrypt)
- Configure automated backups
- Set up monitoring and alerts
