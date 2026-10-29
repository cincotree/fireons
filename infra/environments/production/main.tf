resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

module "fireons" {
  source = "../../modules/fireons"

  providers = {
    aws           = aws
    aws.us_east_1 = aws.us_east_1
  }

  environment                  = local.environment
  region                       = var.region
  github_repository            = var.github_repository
  github_oidc_provider_arn     = aws_iam_openid_connect_provider.github.arn
  webapp_domain                = var.webapp_domain
  api_domain                   = var.api_domain
  enable_custom_domains        = var.enable_custom_domains
  lambda_web_adapter_layer_arn = var.lambda_web_adapter_layer_arn
  api_reserved_concurrency     = var.api_reserved_concurrency
  captcha_enabled              = var.captcha_enabled
}
