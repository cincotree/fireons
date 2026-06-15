package main

import (
	"github.com/pulumi/pulumi-aws/sdk/v6/go/aws/ec2"
	"github.com/pulumi/pulumi-aws/sdk/v6/go/aws/ecr"
	"github.com/pulumi/pulumi-aws/sdk/v6/go/aws/iam"
	"github.com/pulumi/pulumi-tls/sdk/v5/go/tls"
	"github.com/pulumi/pulumi/sdk/v3/go/pulumi"
	"github.com/pulumi/pulumi/sdk/v3/go/pulumi/config"
)

func main() {
	pulumi.Run(func(ctx *pulumi.Context) error {
		cfg := config.New(ctx, "fireons-infra")
		adminCIDR := cfg.Require("admin_cidr")
		keyPairName := cfg.Require("key_pair_name")
		supabaseDbUrl := cfg.RequireSecret("supabase_db_url")
		jwtSecret := cfg.RequireSecret("jwt_secret")
		secretKey := cfg.RequireSecret("secret_key")

		_ = jwtSecret
		_ = secretKey
		_ = supabaseDbUrl

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

		ctx.Export("elastic_ip", eip.PublicIp)
		ctx.Export("ecr_backend_uri", ecrBackend.RepositoryUrl)
		ctx.Export("ecr_frontend_uri", ecrFrontend.RepositoryUrl)
		ctx.Export("ecr_caddy_uri", ecrCaddy.RepositoryUrl)
		ctx.Export("ssh_private_key", sshKey.PrivateKeyPem)
		ctx.Export("ssh_command", pulumi.Sprintf("ssh -i ~/.ssh/fireons-key.pem ubuntu@%s", eip.PublicIp))

		return nil
	})
}
