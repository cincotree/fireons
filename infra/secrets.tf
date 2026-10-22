resource "aws_secretsmanager_secret" "production" {
  name                    = "fireons/production"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "production" {
  secret_id = aws_secretsmanager_secret.production.id
  secret_string = jsonencode({
    SECRET_KEY        = "REPLACE_ME"
    DATABASE_URL      = "REPLACE_ME"
    ANTHROPIC_API_KEY = "REPLACE_ME"
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}
