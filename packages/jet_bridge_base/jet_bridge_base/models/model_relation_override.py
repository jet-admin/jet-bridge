from sqlalchemy import Column, String, Boolean, Integer, Sequence, Index

from jet_bridge_base.models.base import Base


class ModelRelationOverrideModel(Base):
    __tablename__ = 'model_relation_override'

    id = Column(Integer, Sequence('id_seq', start=1), primary_key=True)

    connection_id = Column(String)
    model = Column(String)
    draft = Column(Boolean)
    name = Column(String)
    direction = Column(String)
    local_field = Column(String)
    related_model = Column(String)
    related_field = Column(String)

    __table_args__ = (
        Index('model_draft', connection_id, model, draft),
    )

    def __repr__(self):
        return '{} {} {}'.format(self.connection_id, self.model, self.draft)
