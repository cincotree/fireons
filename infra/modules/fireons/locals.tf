locals {
  name                             = "${var.project}-${var.environment}"
  api_function                     = "${var.project}-${var.environment}-api"
  jobs_family                      = "${var.project}-${var.environment}-jobs"
  jobs_task_definition_arn_pattern = "arn:aws:ecs:${var.region}:${data.aws_caller_identity.current.account_id}:task-definition/${var.project}-${var.environment}-jobs:*"
  webapp_url                       = var.enable_custom_domains ? "https://${var.webapp_domain}" : "https://${aws_cloudfront_distribution.webapp.domain_name}"
  api_base_url                     = var.enable_custom_domains ? "https://${var.api_domain}" : "https://${aws_cloudfront_distribution.api.domain_name}"
}
