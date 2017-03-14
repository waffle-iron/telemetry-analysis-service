# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
import constance
from ..provisioners import Provisioner


class ClusterProvisioner(Provisioner):
    log_dir = 'clusters'

    def __init__(self):
        super().__init__()
        # the S3 URI to the zeppelin setup step
        self.zeppelin_uri = (
            's3://%s/steps/zeppelin/zeppelin.sh' %
            self.config['SPARK_EMR_BUCKET']
        )

    def job_flow_params(self, *args, **kwargs):
        params = super().job_flow_params(*args, **kwargs)
        # don't auto-terminate the cluster
        params.setdefault('Instances', {})['KeepJobFlowAliveWhenNoSteps'] = True
        emr_release = kwargs.get('emr_release')
        zeppelin_application = 'Zeppelin'
        params.setdefault('Applications', []).append({
            'Name': zeppelin_application
        })
        return params

    def start(self, user_email, identifier, emr_release, size, public_key):
        """
        Given the parameters spawns a cluster with the desired properties and
        returns the jobflow ID.
        """
        job_flow_params = self.job_flow_params(
            user_email=user_email,
            identifier=identifier,
            emr_release=emr_release,
            size=size,
        )

        job_flow_params.update({
            'BootstrapActions': [{
                'Name': 'setup-telemetry-cluster',
                'ScriptBootstrapAction': {
                    'Path': self.script_uri,
                    'Args': [
                        '--public-key', public_key,
                        '--email', user_email,
                        '--efs-dns', constance.config.AWS_EFS_DNS,
                    ]
                }
            }],
            'Steps': [{
                'Name': 'setup-zeppelin',
                'ActionOnFailure': 'TERMINATE_JOB_FLOW',
                'HadoopJarStep': {
                    'Jar': self.jar_uri,
                    'Args': [
                        self.zeppelin_uri
                    ]
                }
            }]
        })
        cluster = self.emr.run_job_flow(**job_flow_params)
        return cluster['JobFlowId']

    def info(self, jobflow_id):
        """
        Returns the cluster info for the cluster with the given Jobflow ID
        with the fields start time, state and public IP address
        """
        cluster = self.emr.describe_cluster(ClusterId=jobflow_id)['Cluster']
        return self.format_info(cluster)

    def format_info(self, cluster):
        status = cluster['Status']
        timeline = cluster['Status']['Timeline']
        return {
            'start_time': timeline['CreationDateTime'],
            'state': status['State'],
            'state_change_reason': status.get('StateChangeReason', None),
            'public_dns': cluster.get('MasterPublicDnsName'),
        }

    def list(self, created_after, created_before=None):
        """
        Returns a list of cluster infos in the given time frame with the fields:
        - Jobflow ID
        - state
        - start time
        """
        # set some parameters so we don't get *all* clusters ever
        params = {'CreatedAfter': created_after}
        if created_before is not None:
            params['CreatedBefore'] = created_before

        clusters = []
        list_cluster_paginator = self.emr.get_paginator('list_clusters')
        for page in list_cluster_paginator.paginate(**params):
            for cluster in page.get('Clusters', []):
                clusters.append(self.format_list(cluster))
        return clusters

    def format_list(self, cluster):
        """
        Formats the data returned by the EMR API for internal ATMO use.
        """
        return {
            'jobflow_id': cluster['Id'],
            'state': cluster['Status']['State'],
            'start_time': cluster['Status']['Timeline']['CreationDateTime'],
        }

    def stop(self, jobflow_id):
        """
        Stops the cluster with the given JobFlow ID.
        """
        self.emr.terminate_job_flows(JobFlowIds=[jobflow_id])
