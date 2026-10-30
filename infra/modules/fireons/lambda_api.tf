data "archive_file" "api_placeholder" {
  type        = "zip"
  output_path = "${path.root}/.terraform/api-placeholder.zip"

  source {
    content  = "#!/bin/sh\nexec python3 -m http.server \"$${AWS_LWA_PORT:-8000}\"\n"
    filename = "run.sh"
  }
}

data "aws_iam_policy_document" "lambda_trust" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "api" {
  name               = "${local.name}-api"
  assume_role_policy = data.aws_iam_policy_document.lambda_trust.json
}

resource "aws_iam_role_policy_attachment" "api_logs" {
  role       = aws_iam_role.api.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "api_secret" {
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.this.arn]
  }
}

resource "aws_iam_role_policy" "api_secret" {
  name   = "read-secret"
  role   = aws_iam_role.api.id
  policy = data.aws_iam_policy_document.api_secret.json
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/${local.name}-api"
  retention_in_days = 14
}

resource "aws_lambda_function" "api" {
  function_name                  = "${local.name}-api"
  role                           = aws_iam_role.api.arn
  runtime                        = "python3.12"
  architectures                  = ["arm64"]
  handler                        = "run.sh"
  memory_size                    = var.api_memory_mb
  timeout                        = 30
  publish                        = true
  reserved_concurrent_executions = var.api_reserved_concurrency
  layers                         = [var.lambda_web_adapter_layer_arn]
  filename                       = data.archive_file.api_placeholder.output_path
  source_code_hash               = data.archive_file.api_placeholder.output_base64sha256

  environment {
    variables = {
      AWS_LAMBDA_EXEC_WRAPPER      = "/opt/bootstrap"
      AWS_LWA_PORT                 = "8000"
      AWS_LWA_READINESS_CHECK_PATH = "/health"
      APP_ENV                      = var.environment
      CORS_ORIGINS                 = local.webapp_url
      INGESTION_TEST_ENABLED       = "false"
      INVITE_ONLY                  = tostring(var.invite_only)
      DB_NULL_POOL                 = "false"
      POOL_SIZE                    = "1"
      MAX_OVERFLOW                 = "1"
      EXCHANGE_RATE_SYNC_ENABLED   = "false"
    }
  }

  depends_on = [aws_cloudwatch_log_group.api, aws_iam_role_policy_attachment.api_logs]

  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }
}

resource "aws_lambda_alias" "live" {
  name             = "live"
  function_name    = aws_lambda_function.api.function_name
  function_version = aws_lambda_function.api.version

  lifecycle {
    ignore_changes = [function_version]
  }
}

resource "aws_lambda_function_url" "api" {
  function_name      = aws_lambda_function.api.function_name
  qualifier          = aws_lambda_alias.live.name
  authorization_type = "NONE"
}

resource "aws_lambda_permission" "api_url_invoke_url" {
  statement_id           = "AllowPublicFunctionUrl"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.api.function_name
  qualifier              = aws_lambda_alias.live.name
  principal              = "*"
  function_url_auth_type = "NONE"
}

resource "aws_lambda_permission" "api_url_invoke" {
  statement_id             = "AllowPublicFunctionUrlInvoke"
  action                   = "lambda:InvokeFunction"
  function_name            = aws_lambda_function.api.function_name
  qualifier                = aws_lambda_alias.live.name
  principal                = "*"
  invoked_via_function_url = true
}
