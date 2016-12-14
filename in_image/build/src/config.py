class Config(dict):
    def __init__(self):
        super().__init__({})

    @classmethod
    def load_from_pyfile(cls, file_path):
        ret = cls()
        try:
            with open(file_path) as config_file:
                obj = exec(compile(config_file.read(), file_path, 'exec'), ret)
        except IOError as e:
            e.strerror = 'Unable to load configuration file (%s)' % e.strerror
            raise

        ret._from_object(obj)
        return ret

    def _from_object(self, obj):
        for key in dir(obj):
            if key.isupper():
                self[key] = getattr(obj, key)

