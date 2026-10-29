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
