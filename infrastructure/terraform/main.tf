terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Variables
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "cloudsense"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

# Outputs
output "frontend_url" {
  description = "Frontend CloudFront URL"
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "api_url" {
  description = "Backend API URL"
  value       = aws_ecs_service.backend.load_balancer[0].dns_name
}

