from sqlalchemy import Column, Integer, Sequence, String, DateTime

from jet_bridge.models import Base


class Token(Base):
    __tablename__ = '__jet__token'
    id = Column(Integer, Sequence('token_id_seq'), primary_key=True)
    project = Column(String(64))
    token = Column(String(32))
    date_add = Column(DateTime(timezone=True))

    def __repr__(self):
        return '<Token(project=\'%s\', token=\'%s\', date_add=\'%s\')>' % (self.project, self.token, self.date_add)
