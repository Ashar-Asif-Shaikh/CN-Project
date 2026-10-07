#!/usr/bin/env bash
# deploy_cloudshell.sh - One-click deployment script for AWS CloudShell or AWS CLI
set -e

STACK_NAME="cn-project-team1"
REGION="${AWS_DEFAULT_REGION:-ap-south-1}" # Default to Mumbai (ap-south-1) or your current region

echo "=========================================================="
echo " Deploying CN Course Project on AWS (Free Tier Eligible)  "
echo " Region: $REGION | Stack: $STACK_NAME                    "
echo "=========================================================="

# Check if template exists locally or download
if [ ! -f "cloudformation.yaml" ]; then
    echo "Using local cloudformation.yaml or specify path..."
fi

echo "[1/3] Creating CloudFormation Stack..."
aws cloudformation create-stack \
  --stack-name "$STACK_NAME" \
  --template-body file://cloudformation.yaml \
  --parameters ParameterKey=InstanceType,ParameterValue=t2.micro \
  --region "$REGION"

echo "[2/3] Waiting for stack resources to launch (takes ~3 minutes)..."
aws cloudformation wait stack-create-complete \
  --stack-name "$STACK_NAME" \
  --region "$REGION"

echo ""
echo "=========================================================="
echo " Stack Created Successfully!"
echo " Deployment Outputs:"
echo "=========================================================="
aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query "Stacks[0].Outputs" \
  --output table

echo ""
echo "=========================================================="
echo " To delete all resources after your demo (stops billing): "
echo "   aws cloudformation delete-stack --stack-name $STACK_NAME --region $REGION"
echo "=========================================================="
