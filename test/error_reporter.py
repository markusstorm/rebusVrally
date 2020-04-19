class ErrorReporter:
    def __init__(self):
        self.errors = []

    @staticmethod
    def report_error(error):
        ErrorReporter._instance().errors.append(error)
        print("ERROR: {0}".format(error))

    @staticmethod
    def has_errors():
        return len(ErrorReporter._instance().errors) > 0

    INSTANCE = None
    @staticmethod
    def _instance():
        if ErrorReporter.INSTANCE is None:
            ErrorReporter.INSTANCE = ErrorReporter()
        return ErrorReporter.INSTANCE
