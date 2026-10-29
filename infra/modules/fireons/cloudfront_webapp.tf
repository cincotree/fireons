data "aws_cloudfront_cache_policy" "caching_optimized" {
  name = "Managed-CachingOptimized"
}

resource "aws_s3_bucket" "webapp" {
  bucket = "${local.name}-webapp-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_public_access_block" "webapp" {
  bucket                  = aws_s3_bucket.webapp.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "webapp" {
  bucket = aws_s3_bucket.webapp.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_cloudfront_origin_access_control" "webapp" {
  name                              = "${local.name}-webapp"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_function" "webapp_rewrite" {
  name    = "${local.name}-webapp-rewrite"
  runtime = "cloudfront-js-2.0"
  publish = true
  code    = <<-EOT
    function handler(event) {
      var request = event.request;
      var uri = request.uri;
      if (uri.endsWith('/')) {
        request.uri = uri + 'index.html';
      } else if (uri.lastIndexOf('.') < uri.lastIndexOf('/')) {
        request.uri = uri + '/index.html';
      }
      return request;
    }
  EOT
}

resource "aws_cloudfront_response_headers_policy" "webapp" {
  name = "${local.name}-webapp-security"

  security_headers_config {
    strict_transport_security {
      access_control_max_age_sec = 63072000
      include_subdomains         = true
      preload                    = true
      override                   = true
    }

    referrer_policy {
      referrer_policy = "strict-origin-when-cross-origin"
      override        = true
    }

    content_type_options {
      override = true
    }

    frame_options {
      frame_option = "DENY"
      override     = true
    }

    content_security_policy {
      content_security_policy = join("; ", [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' https://challenges.cloudflare.com",
        "frame-src https://challenges.cloudflare.com",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data:",
        "font-src 'self' data:",
        "connect-src 'self' ${var.enable_custom_domains ? "https://${var.api_domain}" : "https://*.cloudfront.net"}",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
      ])
      override = true
    }
  }
}

resource "aws_cloudfront_distribution" "webapp" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "${local.name} webapp"
  default_root_object = "index.html"
  price_class         = "PriceClass_200"
  aliases             = var.enable_custom_domains ? [var.webapp_domain] : []

  origin {
    origin_id                = "webapp-bucket"
    domain_name              = aws_s3_bucket.webapp.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.webapp.id
  }

  default_cache_behavior {
    target_origin_id           = "webapp-bucket"
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD", "OPTIONS"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = data.aws_cloudfront_cache_policy.caching_optimized.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.webapp.id

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.webapp_rewrite.arn
    }
  }

  custom_error_response {
    error_code            = 403
    response_code         = 404
    response_page_path    = "/404.html"
    error_caching_min_ttl = 10
  }

  custom_error_response {
    error_code            = 404
    response_code         = 404
    response_page_path    = "/404.html"
    error_caching_min_ttl = 10
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = var.enable_custom_domains ? null : true
    acm_certificate_arn            = var.enable_custom_domains ? aws_acm_certificate.webapp.arn : null
    ssl_support_method             = var.enable_custom_domains ? "sni-only" : null
    minimum_protocol_version       = var.enable_custom_domains ? "TLSv1.2_2021" : null
  }
}

data "aws_iam_policy_document" "webapp_bucket" {
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.webapp.arn}/*"]

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.webapp.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "webapp" {
  bucket = aws_s3_bucket.webapp.id
  policy = data.aws_iam_policy_document.webapp_bucket.json

  depends_on = [aws_s3_bucket_public_access_block.webapp]
}
