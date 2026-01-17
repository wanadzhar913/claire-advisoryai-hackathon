#!/bin/sh
set -e

sleep 5

NEW_USER="localuser"
POLICY_NAME="localuser-policy"

# Set up alias 'local' so mc can talk to Minio server
mc alias set local http://minio:9000 "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}"

# Create a bucket (ignored if it doesn't exist)
mc mb --ignore-existing local/"${MINIO_BUCKET_NAME}"

# Check if user already exists
if mc admin user info local "${NEW_USER}" > /dev/null 2>&1; then
    echo "User ${NEW_USER} already exists --skipping creation."
else
    # Create a new user
    echo "Creating user ${NEW_USER}..."
    mc admin user add local "${NEW_USER}" "${MINIO_SECRET_KEY}"

    # Create an access key for the new user
    echo "Creating access key for user ${NEW_USER}..."
    mc admin accesskey create local "${NEW_USER}" \
    --access-key "${MINIO_ACCESS_KEY}" \
    --secret-key "${MINIO_SECRET_KEY}"
fi

# Create policy JSON (read/write access for a spcefic bucket)
cat > /tmp/${POLICY_NAME}.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "BucketAccess",
            "Effect": "Allow",
            "Action": [
                "s3:GetBucketLocation",
                "s3:ListBucket",
                "s3:ListBucketMultipartUploads"
            ],
            "Resource": "arn:aws:s3:::${MINIO_BUCKET_NAME}"
        },
        {
            "Sid": "ObjectAccess",
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListMultipartUploadParts"
            ],
            "Resource": "arn:aws:s3:::${MINIO_BUCKET_NAME}/*"
        }
    ]
}
EOF

# Add policy (if not already present)
if mc admin policy info local "${POLICY_NAME}" > /dev/null 2>&1; then
    echo "Policy ${POLICY_NAME} already exists --skipping creation."
else
    echo "Creating policy ${POLICY_NAME}..."
    mc admin policy create local "${POLICY_NAME}" /tmp/${POLICY_NAME}.json
fi

# Attach policy to user
echo "Attaching policy ${POLICY_NAME} to user ${NEW_USER}..."
mc admin policy attach local "${POLICY_NAME}" --user "${NEW_USER}"

# Clean up
rm /tmp/${POLICY_NAME}.json

echo "User ${NEW_USER} created successfully with access key ${MINIO_ACCESS_KEY}."
