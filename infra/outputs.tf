output "github_deploy_role_arn" {
  value = aws_iam_role.github_deploy.arn
}

output "secret_arn" {
  value = aws_secretsmanager_secret.production.arn
}

output "alarm_topic_arn" {
  value = aws_sns_topic.alarms.arn
}

output "app_certificate_arn" {
  value = aws_acm_certificate.app.arn
}

output "api_certificate_arn" {
  value = aws_acm_certificate.api.arn
}

output "certificate_validation_records" {
  value = {
    for cert in [aws_acm_certificate.app, aws_acm_certificate.api] :
    cert.domain_name => [
      for o in cert.domain_validation_options : {
        name  = o.resource_record_name
        type  = o.resource_record_type
        value = o.resource_record_value
      }
    ]
  }
}
