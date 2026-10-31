locals {
  name         = "${var.project}-${var.environment}"
  api_function = "${var.project}-${var.environment}-api"
  webapp_url   = var.enable_custom_domains ? "https://${var.webapp_domain}" : "https://${aws_cloudfront_distribution.webapp.domain_name}"
  api_base_url = var.enable_custom_domains ? "https://${var.api_domain}" : "https://${aws_cloudfront_distribution.api.domain_name}"
}
