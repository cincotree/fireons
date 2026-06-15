package main

import (
	"github.com/pulumi/pulumi-aws/sdk/v6/go/aws"
	"github.com/pulumi/pulumi-aws/sdk/v6/go/aws/ec2"
	"github.com/pulumi/pulumi-aws/sdk/v6/go/aws/ecr"
	"github.com/pulumi/pulumi-aws/sdk/v6/go/aws/iam"
	"github.com/pulumi/pulumi-aws/sdk/v6/go/aws/rds"
	"github.com/pulumi/pulumi-aws/sdk/v6/go/aws/sns"
	"github.com/pulumi/pulumi-aws/sdk/v6/go/aws/cloudwatch"
	"github.com/pulumi/pulumi-tls/sdk/v5/go/tls"
	"github.com/pulumi/pulumi/sdk/v3/go/pulumi"
	"github.com/pulumi/pulumi/sdk/v3/go/pulumi/config"
)

func main() {
	pulumi.Run(func(ctx *pulumi.Context) error {
		cfg := config.New(ctx, "fireons-infra")
		domain := cfg.Require("domain")
		adminCIDR := cfg.Require("admin_cidr")
		keyPairName := cfg.Require("key_pair_name")
		dbPassword := cfg.RequireSecret("db_password")
		jwtSecret := cfg.RequireSecret("jwt_secret")
		secretKey := cfg.RequireSecret("secret_key")
		alertEmail := cfg.Require("alert_email")

		_ = domain
		_ = jwtSecret
		_ = secretKey

		sshKey, err := tls.NewPrivateKey(ctx, "fireons-key", &tls.PrivateKeyArgs{
			Algorithm: pulumi.String("RSA"),
			RsaBits:   pulumi.Int(4096),
		})
		if err != nil {
			return err
		}

		keyPair, err := ec2.NewKeyPair(ctx, "fireons-key", &ec2.KeyPairArgs{
			KeyName:   pulumi.String(keyPairName),
			PublicKey: sshKey.PublicKeyOpenssh,
		})
		if err != nil {
			return err
		}

		vpc, err := ec2.LookupVpc(ctx, &ec2.LookupVpcArgs{
			Default: pulumi.BoolRef(true),
		})
		if err != nil {
			return err
		}

		azs, err := aws.GetAvailabilityZones(ctx, &aws.GetAvailabilityZonesArgs{
			State: pulumi.StringRef("available"),
		})
		if err != nil {
			return err
		}

		subnet1, err := ec2.NewSubnet(ctx, "fireons-subnet-1", &ec2.SubnetArgs{
			VpcId:            pulumi.String(vpc.Id),
			CidrBlock:        pulumi.String("172.31.48.0/20"),
			AvailabilityZone: pulumi.String(azs.Names[0]),
		})
		if err != nil {
			return err
		}

		subnet2, err := ec2.NewSubnet(ctx, "fireons-subnet-2", &ec2.SubnetArgs{
			VpcId:            pulumi.String(vpc.Id),
			CidrBlock:        pulumi.String("172.31.64.0/20"),
			AvailabilityZone: pulumi.String(azs.Names[1]),
		})
		if err != nil {
			return err
		}

		ec2SG, err := ec2.NewSecurityGroup(ctx, "fireons-ec2-sg", &ec2.SecurityGroupArgs{
			VpcId:       pulumi.String(vpc.Id),
			Description: pulumi.String("Security group for Fireons EC2 instance"),
			Ingress: ec2.SecurityGroupIngressArray{
				&ec2.SecurityGroupIngressArgs{
					Protocol:    pulumi.String("tcp"),
					FromPort:    pulumi.Int(22),
					ToPort:      pulumi.Int(22),
					CidrBlocks:  pulumi.StringArray{pulumi.String(adminCIDR)},
					Description: pulumi.String("SSH"),
				},
				&ec2.SecurityGroupIngressArgs{
					Protocol:    pulumi.String("tcp"),
					FromPort:    pulumi.Int(80),
					ToPort:      pulumi.Int(80),
					CidrBlocks:  pulumi.StringArray{pulumi.String("0.0.0.0/0")},
					Description: pulumi.String("HTTP"),
				},
				&ec2.SecurityGroupIngressArgs{
					Protocol:    pulumi.String("tcp"),
					FromPort:    pulumi.Int(443),
					ToPort:      pulumi.Int(443),
					CidrBlocks:  pulumi.StringArray{pulumi.String("0.0.0.0/0")},
					Description: pulumi.String("HTTPS"),
				},
			},
			Egress: ec2.SecurityGroupEgressArray{
				&ec2.SecurityGroupEgressArgs{
					Protocol:   pulumi.String("-1"),
					FromPort:   pulumi.Int(0),
					ToPort:     pulumi.Int(0),
					CidrBlocks: pulumi.StringArray{pulumi.String("0.0.0.0/0")},
				},
			},
			Tags: pulumi.StringMap{
				"Name": pulumi.String("fireons-ec2-sg"),
			},
		})
		if err != nil {
			return err
		}

		rdsSG, err := ec2.NewSecurityGroup(ctx, "fireons-rds-sg", &ec2.SecurityGroupArgs{
			VpcId:       pulumi.String(vpc.Id),
			Description: pulumi.String("Security group for Fireons RDS instance"),
			Ingress: ec2.SecurityGroupIngressArray{
				&ec2.SecurityGroupIngressArgs{
					Protocol:       pulumi.String("tcp"),
					FromPort:       pulumi.Int(5432),
					ToPort:         pulumi.Int(5432),
					SecurityGroups: pulumi.StringArray{ec2SG.ID()},
					Description:    pulumi.String("PostgreSQL from EC2"),
				},
			},
			Egress: ec2.SecurityGroupEgressArray{
				&ec2.SecurityGroupEgressArgs{
					Protocol:   pulumi.String("-1"),
					FromPort:   pulumi.Int(0),
					ToPort:     pulumi.Int(0),
					CidrBlocks: pulumi.StringArray{pulumi.String("0.0.0.0/0")},
				},
			},
			Tags: pulumi.StringMap{
				"Name": pulumi.String("fireons-rds-sg"),
			},
		})
		if err != nil {
			return err
		}

		ec2Role, err := iam.NewRole(ctx, "fireons-ec2-role", &iam.RoleArgs{
			AssumeRolePolicy: pulumi.String(`{
				"Version": "2012-10-17",
				"Statement": [{
					"Effect": "Allow",
					"Principal": { "Service": "ec2.amazonaws.com" },
					"Action": "sts:AssumeRole"
				}]
			}`),
			Description: pulumi.String("IAM role for Fireons EC2 instance"),
		})
		if err != nil {
			return err
		}

		_, err = iam.NewRolePolicyAttachment(ctx, "fireons-ecr-readonly", &iam.RolePolicyAttachmentArgs{
			Role:      ec2Role.Name,
			PolicyArn: pulumi.String("arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"),
		})
		if err != nil {
			return err
		}

		_, err = iam.NewRolePolicyAttachment(ctx, "fireons-cloudwatch-agent", &iam.RolePolicyAttachmentArgs{
			Role:      ec2Role.Name,
			PolicyArn: pulumi.String("arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"),
		})
		if err != nil {
			return err
		}

		ec2InstanceProfile, err := iam.NewInstanceProfile(ctx, "fireons-ec2-profile", &iam.InstanceProfileArgs{
			Role: ec2Role.Name,
		})
		if err != nil {
			return err
		}

		ami, err := ec2.LookupAmi(ctx, &ec2.LookupAmiArgs{
			Owners:     []string{"099720109477"},
			MostRecent: pulumi.BoolRef(true),
			Filters: []ec2.GetAmiFilter{
				{
					Name:   "name",
					Values: []string{"ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"},
				},
				{
					Name:   "virtualization-type",
					Values: []string{"hvm"},
				},
			},
		})
		if err != nil {
			return err
		}

		instance, err := ec2.NewInstance(ctx, "fireons-instance", &ec2.InstanceArgs{
			InstanceType:               pulumi.String("t3.small"),
			Ami:                        pulumi.String(ami.Id),
			KeyName:                    keyPair.KeyName,
			VpcSecurityGroupIds:        pulumi.StringArray{ec2SG.ID()},
			IamInstanceProfile:         ec2InstanceProfile.Name,
			AssociatePublicIpAddress:   pulumi.Bool(true),
			RootBlockDevice: &ec2.InstanceRootBlockDeviceArgs{
				VolumeSize: pulumi.Int(20),
				VolumeType: pulumi.String("gp3"),
			},
			MetadataOptions: &ec2.InstanceMetadataOptionsArgs{
				HttpTokens: pulumi.String("required"),
			},
			Tags: pulumi.StringMap{
				"Name": pulumi.String("fireons-app"),
			},
		})
		if err != nil {
			return err
		}

		eip, err := ec2.NewEip(ctx, "fireons-eip", &ec2.EipArgs{
			Instance: instance.ID(),
			Domain:   pulumi.String("vpc"),
			Tags: pulumi.StringMap{
				"Name": pulumi.String("fireons-eip"),
			},
		})
		if err != nil {
			return err
		}

		ecrBackend, err := ecr.NewRepository(ctx, "fireons-backend", &ecr.RepositoryArgs{
			Name: pulumi.String("fireons-backend"),
			ImageScanningConfiguration: &ecr.RepositoryImageScanningConfigurationArgs{
				ScanOnPush: pulumi.Bool(true),
			},
			Tags: pulumi.StringMap{
				"Name": pulumi.String("fireons-backend"),
			},
		})
		if err != nil {
			return err
		}

		ecrFrontend, err := ecr.NewRepository(ctx, "fireons-frontend", &ecr.RepositoryArgs{
			Name: pulumi.String("fireons-frontend"),
			ImageScanningConfiguration: &ecr.RepositoryImageScanningConfigurationArgs{
				ScanOnPush: pulumi.Bool(true),
			},
			Tags: pulumi.StringMap{
				"Name": pulumi.String("fireons-frontend"),
			},
		})
		if err != nil {
			return err
		}

		ecrCaddy, err := ecr.NewRepository(ctx, "fireons-caddy", &ecr.RepositoryArgs{
			Name: pulumi.String("fireons-caddy"),
			ImageScanningConfiguration: &ecr.RepositoryImageScanningConfigurationArgs{
				ScanOnPush: pulumi.Bool(true),
			},
			Tags: pulumi.StringMap{
				"Name": pulumi.String("fireons-caddy"),
			},
		})
		if err != nil {
			return err
		}

		subnetGroup, err := rds.NewSubnetGroup(ctx, "fireons-db-subnets", &rds.SubnetGroupArgs{
			SubnetIds: pulumi.StringArray{subnet1.ID(), subnet2.ID()},
			Tags: pulumi.StringMap{
				"Name": pulumi.String("fireons-db-subnets"),
			},
		})
		if err != nil {
			return err
		}

		rdsMonitorRole, err := iam.NewRole(ctx, "fireons-rds-monitor-role", &iam.RoleArgs{
			AssumeRolePolicy: pulumi.String(`{
				"Version": "2012-10-17",
				"Statement": [{
					"Effect": "Allow",
					"Principal": { "Service": "monitoring.rds.amazonaws.com" },
					"Action": "sts:AssumeRole"
				}]
			}`),
			Description: pulumi.String("IAM role for RDS enhanced monitoring"),
		})
		if err != nil {
			return err
		}

		_, err = iam.NewRolePolicyAttachment(ctx, "fireons-rds-monitor-policy", &iam.RolePolicyAttachmentArgs{
			Role:      rdsMonitorRole.Name,
			PolicyArn: pulumi.String("arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"),
		})
		if err != nil {
			return err
		}

		rdsInstance, err := rds.NewInstance(ctx, "fireons-db", &rds.InstanceArgs{
			Engine:                          pulumi.String("postgres"),
			EngineVersion:                   pulumi.String("16"),
			InstanceClass:                   pulumi.String("db.t3.micro"),
			AllocatedStorage:                pulumi.Int(20),
			StorageType:                     pulumi.String("gp3"),
			StorageEncrypted:                pulumi.Bool(true),
			DbName:                          pulumi.String("fireons_prod"),
			Username:                        pulumi.String("fireons"),
			Password:                        dbPassword,
			DbSubnetGroupName:               subnetGroup.Name,
			VpcSecurityGroupIds:             pulumi.StringArray{rdsSG.ID()},
			MultiAz:                         pulumi.Bool(false),
			PubliclyAccessible:              pulumi.Bool(false),
			BackupRetentionPeriod:           pulumi.Int(7),
			DeletionProtection:              pulumi.Bool(true),
			SkipFinalSnapshot:               pulumi.Bool(false),
			AutoMinorVersionUpgrade:         pulumi.Bool(true),
			PerformanceInsightsEnabled:      pulumi.Bool(true),
			PerformanceInsightsRetentionPeriod: pulumi.Int(7),
			EnabledCloudwatchLogsExports:    pulumi.StringArray{pulumi.String("postgresql")},
			MonitoringRoleArn:               rdsMonitorRole.Arn,
			MonitoringInterval:              pulumi.Int(60),
			Tags: pulumi.StringMap{
				"Name": pulumi.String("fireons-db"),
			},
		})
		if err != nil {
			return err
		}

		snsTopic, err := sns.NewTopic(ctx, "fireons-alerts", &sns.TopicArgs{
			Name: pulumi.String("fireons-alerts"),
		})
		if err != nil {
			return err
		}

		_, err = sns.NewTopicSubscription(ctx, "fireons-alert-email", &sns.TopicSubscriptionArgs{
			Topic:    snsTopic.Arn,
			Protocol: pulumi.String("email"),
			Endpoint: pulumi.String(alertEmail),
		})
		if err != nil {
			return err
		}

		_, err = cloudwatch.NewMetricAlarm(ctx, "fireons-cpu-high", &cloudwatch.MetricAlarmArgs{
			Name:               pulumi.String("fireons-ec2-cpu-high"),
			ComparisonOperator: pulumi.String("GreaterThanThreshold"),
			EvaluationPeriods:  pulumi.Int(10),
			MetricName:         pulumi.String("CPUUtilization"),
			Namespace:          pulumi.String("AWS/EC2"),
			Period:             pulumi.Int(60),
			Statistic:          pulumi.String("Average"),
			Threshold:          pulumi.Float64(80),
			AlarmDescription:   pulumi.String("EC2 CPU > 80% for 10 minutes"),
			AlarmActions:       pulumi.Array{snsTopic.Arn},
			Dimensions:         pulumi.StringMap{"InstanceId": instance.ID()},
		})
		if err != nil {
			return err
		}

		_, err = cloudwatch.NewMetricAlarm(ctx, "fireons-rds-cpu-high", &cloudwatch.MetricAlarmArgs{
			Name:               pulumi.String("fireons-rds-cpu-high"),
			ComparisonOperator: pulumi.String("GreaterThanThreshold"),
			EvaluationPeriods:  pulumi.Int(10),
			MetricName:         pulumi.String("CPUUtilization"),
			Namespace:          pulumi.String("AWS/RDS"),
			Period:             pulumi.Int(60),
			Statistic:          pulumi.String("Average"),
			Threshold:          pulumi.Float64(70),
			AlarmDescription:   pulumi.String("RDS CPU > 70% for 10 minutes"),
			AlarmActions:       pulumi.Array{snsTopic.Arn},
			Dimensions:         pulumi.StringMap{"DBInstanceIdentifier": rdsInstance.ID()},
		})
		if err != nil {
			return err
		}

		_, err = cloudwatch.NewMetricAlarm(ctx, "fireons-rds-storage-low", &cloudwatch.MetricAlarmArgs{
			Name:               pulumi.String("fireons-rds-storage-low"),
			ComparisonOperator: pulumi.String("LessThanThreshold"),
			EvaluationPeriods:  pulumi.Int(1),
			MetricName:         pulumi.String("FreeStorageSpace"),
			Namespace:          pulumi.String("AWS/RDS"),
			Period:             pulumi.Int(60),
			Statistic:          pulumi.String("Average"),
			Threshold:          pulumi.Float64(2000000000),
			AlarmDescription:   pulumi.String("RDS free storage < 2GB"),
			AlarmActions:       pulumi.Array{snsTopic.Arn},
			Dimensions:         pulumi.StringMap{"DBInstanceIdentifier": rdsInstance.ID()},
		})
		if err != nil {
			return err
		}

		ctx.Export("elastic_ip", eip.PublicIp)
		ctx.Export("rds_host", rdsInstance.Endpoint)
		ctx.Export("ecr_backend_uri", ecrBackend.RepositoryUrl)
		ctx.Export("ecr_frontend_uri", ecrFrontend.RepositoryUrl)
		ctx.Export("ecr_caddy_uri", ecrCaddy.RepositoryUrl)
		ctx.Export("ssh_private_key", sshKey.PrivateKeyPem)
		ctx.Export("ssh_command", pulumi.Sprintf("ssh -i ~/.ssh/fireons-key.pem ubuntu@%s", eip.PublicIp))

		return nil
	})
}
