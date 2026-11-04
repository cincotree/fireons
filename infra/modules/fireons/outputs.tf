output "secret_arn" {
  value = aws_secretsmanager_secret.this.arn
}

output "certificate_validation_records" {
  value = {
    for cert in [aws_acm_certificate.webapp, aws_acm_certificate.api] :
    cert.domain_name => [
      for o in cert.domain_validation_options : {
        name  = o.resource_record_name
        type  = o.resource_record_type
        value = o.resource_record_value
      }
    ]
  }
}

output "webapp_url" {
  value = local.webapp_url
}

output "api_base_url" {
  value = local.api_base_url
}

output "webapp_distribution_domain_name" {
  value = aws_cloudfront_distribution.webapp.domain_name
}

output "api_distribution_domain_name" {
  value = aws_cloudfront_distribution.api.domain_name
}

output "github_environment_variables" {
  value = {
    AWS_DEPLOY_ROLE_ARN      = aws_iam_role.github_deploy.arn
    AWS_REGION               = var.region
    WEBAPP_BUCKET            = aws_s3_bucket.webapp.bucket
    WEBAPP_DISTRIBUTION_ID   = aws_cloudfront_distribution.webapp.id
    WEBAPP_URL               = local.webapp_url
    NEXT_PUBLIC_API_BASE_URL = local.api_base_url
  }
}
