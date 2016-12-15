from datetime import datetime

from peewee import Model, IntegerField, DateField, BigIntegerField, CharField, DateTimeField

from src.database import db


class BaseModel(Model):
    class Meta:
        database = db


# below are read-write tables
class TransferRecord(BaseModel):
    id = IntegerField(primary_key=True)
    org_id = IntegerField()
    date = DateField()
    size = BigIntegerField()
    created_at = DateTimeField()

    class Meta:
        db_table = 'transfer_record'


class TransferStatement(BaseModel):
    id = IntegerField(primary_key=True)
    org_id = IntegerField()
    month = DateField()
    plan_id = IntegerField()
    used = IntegerField(default=0)

    class Meta:
        db_table = 'transfer_statement'


# below are read-only tables
class Org(BaseModel):
    id = IntegerField(primary_key=True)
    name = CharField()
    flag = IntegerField(default=0)

    @property
    def current_org_plan(self):
        org_plans = OrgsPlans.select().where(OrgsPlans.org_id == self.id).order_by(OrgsPlans.start_date.desc(),
                                                                                   OrgsPlans.id.desc())
        current_date = datetime.utcnow().date()
        _current_org_plan = None
        for org_plan in org_plans:
            if org_plan.start_date <= current_date:
                _current_org_plan = org_plan
                break
        return _current_org_plan

    class Meta:
        db_table = 'org'


class OrgsPlans(BaseModel):
    id = IntegerField(primary_key=True)
    org_id = IntegerField()
    start_date = DateField()
    end_date = DateField()
    plan_id = IntegerField()

    @property
    def expired(self):
        return datetime.utcnow().date() > self.end_date

    class Meta:
        db_table = 'orgs_plans'
