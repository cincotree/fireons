locals {
  name = "${var.project}-${var.environment}"
}

resource "aws_acm_certificate" "webapp" {
  provider          = aws.us_east_1
  domain_name       = var.webapp_domain
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_acm_certificate" "api" {
  provider          = aws.us_east_1
  domain_name       = var.api_domain
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

locals {
  webapp_url   = var.enable_custom_domains ? "https://${var.webapp_domain}" : "https://${aws_cloudfront_distribution.webapp.domain_name}"
  api_base_url = var.enable_custom_domains ? "https://${var.api_domain}" : "https://${aws_cloudfront_distribution.api.domain_name}"
  cors_origin  = var.enable_custom_domains ? "https://${var.webapp_domain}" : "https://${aws_cloudfront_distribution.webapp.domain_name}"
}
