locals {
  name         = "${var.project}-${var.environment}"
  webapp_url   = var.enable_custom_domains ? "https://${var.webapp_domain}" : "https://${aws_cloudfront_distribution.webapp.domain_name}"
  api_base_url = var.enable_custom_domains ? "https://${var.api_domain}" : "https://${aws_cloudfront_distribution.api.domain_name}"
}
