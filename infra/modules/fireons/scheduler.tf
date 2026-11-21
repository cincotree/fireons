data "aws_iam_policy_document" "scheduler_trust" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  name               = "${local.name}-scheduler"
  assume_role_policy = data.aws_iam_policy_document.scheduler_trust.json
}

data "aws_iam_policy_document" "scheduler" {
  statement {
    actions   = ["ecs:RunTask"]
    resources = [local.jobs_task_definition_arn_pattern]

    condition {
      test     = "ArnEquals"
      variable = "ecs:cluster"
      values   = [aws_ecs_cluster.jobs.arn]
    }
  }

  statement {
    actions   = ["iam:PassRole"]
    resources = [aws_iam_role.jobs_task.arn, aws_iam_role.jobs_execution.arn]
  }
}

resource "aws_iam_role_policy" "scheduler" {
  name   = "run-jobs"
  role   = aws_iam_role.scheduler.id
  policy = data.aws_iam_policy_document.scheduler.json
}

resource "aws_scheduler_schedule_group" "jobs" {
  name = "${local.name}-jobs"
}

resource "aws_scheduler_schedule" "jobs" {
  for_each = var.scheduled_jobs

  name                         = "${local.name}-${each.key}"
  group_name                   = aws_scheduler_schedule_group.jobs.name
  schedule_expression          = each.value.schedule_expression
  schedule_expression_timezone = "UTC"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_ecs_cluster.jobs.arn
    role_arn = aws_iam_role.scheduler.arn
    input = jsonencode({
      containerOverrides = [{
        name        = "jobs"
        environment = [{ name = "JOB_NAME", value = each.value.job }]
      }]
    })

    ecs_parameters {
      task_definition_arn = aws_ecs_task_definition.jobs.arn_without_revision
      launch_type         = "FARGATE"
      task_count          = 1

      network_configuration {
        subnets          = data.aws_subnets.default.ids
        security_groups  = [aws_security_group.jobs.id]
        assign_public_ip = true
      }
    }

    retry_policy {
      maximum_retry_attempts       = 0
      maximum_event_age_in_seconds = 60
    }
  }
}
