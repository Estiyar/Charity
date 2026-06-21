class CharityDatabaseRouter:
    medregistry_app = "medregistry"
    antifraud_app = "antifraud"

    def db_for_read(self, model, **hints):
        return self._database_for_model(model)

    def db_for_write(self, model, **hints):
        return self._database_for_model(model)

    def allow_relation(self, obj1, obj2, **hints):
        return self._database_for_model(obj1.__class__) == self._database_for_model(
            obj2.__class__
        )

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == self.medregistry_app:
            return db == self.medregistry_app
        if app_label == self.antifraud_app:
            return db == self.antifraud_app
        return db == "default"

    def _database_for_model(self, model):
        app_label = model._meta.app_label
        if app_label == self.medregistry_app:
            return self.medregistry_app
        if app_label == self.antifraud_app:
            return self.antifraud_app
        return "default"
