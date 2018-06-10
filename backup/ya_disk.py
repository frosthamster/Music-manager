from YaDiskClient.YaDiskClient import YaDisk, YaDiskException
from .chunk_partitioner import ChunkPartitioner


class YaDiskWithProgress(YaDisk):
    def upload(self, file, path):
        resp = self._sendRequest("PUT", path, data=ChunkPartitioner(file, 'Uploading library'))
        if resp.status_code != 201:
            raise YaDiskException(resp.status_code, resp.content)
