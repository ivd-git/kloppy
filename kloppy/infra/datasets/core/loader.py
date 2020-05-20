from typing import List


class Loader(ABC):

    loaders : List["Loader"] = []

    @abstractmethod
    def load(self, url: str, local_filename: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def supports(self, url: str) -> bool:
        raise NotImplementedError

    @staticmethod
    def get(url: str, local_filename: str) -> None:
        for loader in Loader.loaders:
            if loader.supports(url):
                return loader.load(url, local_filename)
        raise RuntimeError



class HttpLoader(Loader):
    def load(self, url: str, local_filename: str) -> None:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

    def supports(self, url: str) -> bool:
        return url.startswith("http://") or url.startswith("https://")


class S3Loader(Loader):
    def load(self, url: str, local_filename: str) -> None:
        # Get the shit from S3

    def supports(self, url: str) -> bool:
        return url.startswith("s3://")
