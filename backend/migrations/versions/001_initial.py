"""Niezmienna migawka schematu początkowego."""
from alembic import op
import sqlalchemy as sa
revision='001'
down_revision=None
branch_labels=None
depends_on=None

def upgrade():
    """Tworzy pierwszą wersję relacyjnego schematu."""
    op.create_table('articles',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('code', sa.String(length=80), primary_key=False, nullable=False),
        sa.Column('name', sa.Text(), primary_key=False, nullable=False),
        sa.Column('cycle', sa.Integer(), primary_key=False, nullable=False),
        sa.UniqueConstraint('code'),
    )
    op.create_table('login_attempts',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('key', sa.String(length=200), primary_key=False, nullable=False),
        sa.Column('created', sa.DateTime(timezone=True), primary_key=False, nullable=False),
    )
    op.create_index('ix_login_attempts_key', 'login_attempts', ['key'], unique=False)
    op.create_table('methods',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('code', sa.String(length=120), primary_key=False, nullable=False),
        sa.Column('name', sa.Text(), primary_key=False, nullable=False),
        sa.UniqueConstraint('code'),
    )
    op.create_table('users',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('login', sa.String(length=120), primary_key=False, nullable=False),
        sa.Column('password', sa.Text(), primary_key=False, nullable=False),
        sa.Column('role', sa.String(length=30), primary_key=False, nullable=False),
        sa.Column('active', sa.Boolean(), primary_key=False, nullable=False),
        sa.UniqueConstraint('login'),
    )
    op.create_table('article_configs',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('article_id', sa.Integer(), sa.ForeignKey('articles.id'), primary_key=False, nullable=False),
        sa.Column('version', sa.Integer(), primary_key=False, nullable=False),
        sa.Column('author', sa.Integer(), sa.ForeignKey('users.id'), primary_key=False, nullable=False),
        sa.Column('created', sa.DateTime(timezone=True), primary_key=False, nullable=False),
        sa.UniqueConstraint('article_id','version'),
    )
    op.create_index('ix_article_configs_article_id', 'article_configs', ['article_id'], unique=False)
    op.create_table('audit',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('author', sa.Integer(), sa.ForeignKey('users.id'), primary_key=False, nullable=False),
        sa.Column('action', sa.String(length=80), primary_key=False, nullable=False),
        sa.Column('entity', sa.String(length=80), primary_key=False, nullable=False),
        sa.Column('payload', sa.JSON(), primary_key=False, nullable=False),
        sa.Column('created', sa.DateTime(timezone=True), primary_key=False, nullable=False),
    )
    op.create_table('historical_rows',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('file_hash', sa.String(length=64), primary_key=False, nullable=False),
        sa.Column('row_number', sa.Integer(), primary_key=False, nullable=False),
        sa.Column('lot', sa.String(length=120), primary_key=False, nullable=False),
        sa.Column('values', sa.JSON(), primary_key=False, nullable=False),
        sa.Column('issues', sa.JSON(), primary_key=False, nullable=False),
        sa.Column('author', sa.Integer(), sa.ForeignKey('users.id'), primary_key=False, nullable=False),
        sa.UniqueConstraint('file_hash','row_number'),
    )
    op.create_index('ix_historical_rows_lot', 'historical_rows', ['lot'], unique=False)
    op.create_table('login_sessions',
        sa.Column('token_hash', sa.String(length=64), primary_key=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), primary_key=False, nullable=False),
        sa.Column('expires', sa.DateTime(timezone=True), primary_key=False, nullable=False),
        sa.Column('csrf', sa.String(length=80), primary_key=False, nullable=False),
        sa.Column('scopes', sa.JSON(), primary_key=False, nullable=False),
    )
    op.create_table('orders',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('article_id', sa.Integer(), sa.ForeignKey('articles.id'), primary_key=False, nullable=False),
        sa.Column('lot', sa.String(length=120), primary_key=False, nullable=False),
        sa.Column('roll', sa.String(length=120), primary_key=False, nullable=False),
        sa.Column('quantity', sa.String(length=80), primary_key=False, nullable=False),
        sa.Column('reporter', sa.Integer(), sa.ForeignKey('users.id'), primary_key=False, nullable=False),
        sa.Column('created', sa.DateTime(timezone=True), primary_key=False, nullable=False),
        sa.Column('completed', sa.DateTime(timezone=True), primary_key=False, nullable=True),
        sa.Column('status', sa.String(length=30), primary_key=False, nullable=False),
        sa.Column('required_sessions', sa.Integer(), primary_key=False, nullable=False),
        sa.Column('extra', sa.JSON(), primary_key=False, nullable=False),
        sa.UniqueConstraint('article_id','lot','roll'),
    )
    op.create_index('ix_orders_article_id', 'orders', ['article_id'], unique=False)
    op.create_index('ix_orders_lot', 'orders', ['lot'], unique=False)
    op.create_table('characteristics',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('config_id', sa.Integer(), sa.ForeignKey('article_configs.id'), primary_key=False, nullable=False),
        sa.Column('method_id', sa.Integer(), sa.ForeignKey('methods.id'), primary_key=False, nullable=False),
        sa.Column('key', sa.String(length=40), primary_key=False, nullable=False),
        sa.Column('position', sa.Integer(), primary_key=False, nullable=False),
        sa.Column('spec', sa.JSON(), primary_key=False, nullable=False),
        sa.UniqueConstraint('config_id','key'),
    )
    op.create_index('ix_characteristics_config_id', 'characteristics', ['config_id'], unique=False)
    op.create_table('dispositions',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id'), primary_key=False, nullable=False),
        sa.Column('author', sa.Integer(), sa.ForeignKey('users.id'), primary_key=False, nullable=False),
        sa.Column('created', sa.DateTime(timezone=True), primary_key=False, nullable=False),
        sa.Column('held', sa.Boolean(), primary_key=False, nullable=False),
        sa.Column('reason', sa.Text(), primary_key=False, nullable=False),
    )
    op.create_index('ix_dispositions_order_id', 'dispositions', ['order_id'], unique=False)
    op.create_table('lab_sessions',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('article_id', sa.Integer(), sa.ForeignKey('articles.id'), primary_key=False, nullable=False),
        sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id'), primary_key=False, nullable=False),
        sa.Column('config_id', sa.Integer(), sa.ForeignKey('article_configs.id'), primary_key=False, nullable=False),
        sa.Column('cycle', sa.Integer(), primary_key=False, nullable=False),
        sa.Column('revision', sa.Integer(), primary_key=False, nullable=False),
        sa.Column('operator', sa.Integer(), sa.ForeignKey('users.id'), primary_key=False, nullable=False),
        sa.Column('test_date', sa.String(length=10), primary_key=False, nullable=False),
        sa.Column('metadata', sa.JSON(), primary_key=False, nullable=False),
        sa.Column('ok', sa.Boolean(), primary_key=False, nullable=False),
        sa.Column('acknowledged', sa.Boolean(), primary_key=False, nullable=False),
        sa.Column('created', sa.DateTime(timezone=True), primary_key=False, nullable=False),
        sa.Column('correction_of', sa.Integer(), sa.ForeignKey('lab_sessions.id'), primary_key=False, nullable=True),
        sa.Column('reason', sa.Text(), primary_key=False, nullable=False),
        sa.UniqueConstraint('correction_of'),
        sa.UniqueConstraint('article_id','cycle','revision'),
    )
    op.create_index('ix_lab_sessions_article_id', 'lab_sessions', ['article_id'], unique=False)
    op.create_index('ix_lab_sessions_order_id', 'lab_sessions', ['order_id'], unique=False)
    op.create_table('notification_rules',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('characteristic_id', sa.Integer(), sa.ForeignKey('characteristics.id'), primary_key=False, nullable=False),
        sa.Column('email', sa.String(length=254), primary_key=False, nullable=False),
        sa.Column('events', sa.JSON(), primary_key=False, nullable=False),
        sa.Column('enabled', sa.Boolean(), primary_key=False, nullable=False),
    )
    op.create_table('results',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('session_id', sa.Integer(), sa.ForeignKey('lab_sessions.id'), primary_key=False, nullable=False),
        sa.Column('characteristic_id', sa.Integer(), sa.ForeignKey('characteristics.id'), primary_key=False, nullable=False),
        sa.Column('average', sa.Text(), primary_key=False, nullable=True),
        sa.Column('ok', sa.Boolean(), primary_key=False, nullable=False),
        sa.Column('simulated_average', sa.Text(), primary_key=False, nullable=True),
        sa.Column('simulated_ok', sa.Boolean(), primary_key=False, nullable=False),
        sa.UniqueConstraint('session_id','characteristic_id'),
    )
    op.create_index('ix_results_session_id', 'results', ['session_id'], unique=False)
    op.create_table('spc_configs',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('characteristic_id', sa.Integer(), sa.ForeignKey('characteristics.id'), primary_key=False, nullable=False),
        sa.Column('limits', sa.JSON(), primary_key=False, nullable=False),
        sa.Column('sampling_plan', sa.Text(), primary_key=False, nullable=False),
        sa.Column('author', sa.Integer(), sa.ForeignKey('users.id'), primary_key=False, nullable=False),
        sa.Column('created', sa.DateTime(timezone=True), primary_key=False, nullable=False),
    )
    op.create_index('ix_spc_configs_characteristic_id', 'spc_configs', ['characteristic_id'], unique=False)
    op.create_table('alerts',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('session_id', sa.Integer(), sa.ForeignKey('lab_sessions.id'), primary_key=False, nullable=False),
        sa.Column('spc_config_id', sa.Integer(), sa.ForeignKey('spc_configs.id'), primary_key=False, nullable=False),
        sa.Column('event', sa.String(length=40), primary_key=False, nullable=False),
        sa.Column('payload', sa.JSON(), primary_key=False, nullable=False),
        sa.Column('created', sa.DateTime(timezone=True), primary_key=False, nullable=False),
        sa.UniqueConstraint('session_id','spc_config_id','event'),
    )
    op.create_table('measurements',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('result_id', sa.Integer(), sa.ForeignKey('results.id'), primary_key=False, nullable=False),
        sa.Column('position', sa.Integer(), primary_key=False, nullable=False),
        sa.Column('value', sa.Text(), primary_key=False, nullable=False),
        sa.Column('ok', sa.Boolean(), primary_key=False, nullable=False),
        sa.UniqueConstraint('result_id','position'),
    )
    op.create_index('ix_measurements_result_id', 'measurements', ['result_id'], unique=False)
    op.create_table('mail_outbox',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('alert_id', sa.Integer(), sa.ForeignKey('alerts.id'), primary_key=False, nullable=False),
        sa.Column('recipient', sa.String(length=254), primary_key=False, nullable=False),
        sa.Column('status', sa.String(length=30), primary_key=False, nullable=False),
        sa.Column('attempts', sa.Integer(), primary_key=False, nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), primary_key=False, nullable=True),
        sa.Column('error', sa.Text(), primary_key=False, nullable=False),
        sa.UniqueConstraint('alert_id','recipient'),
    )
    op.create_table('simulations',
        sa.Column('measurement_id', sa.Integer(), sa.ForeignKey('measurements.id'), primary_key=True, nullable=False),
        sa.Column('value', sa.Text(), primary_key=False, nullable=False),
        sa.Column('ok', sa.Boolean(), primary_key=False, nullable=False),
        sa.Column('corrected', sa.Boolean(), primary_key=False, nullable=False),
        sa.Column('algorithm', sa.String(length=30), primary_key=False, nullable=False),
        sa.Column('parameters', sa.JSON(), primary_key=False, nullable=False),
        sa.Column('created', sa.DateTime(timezone=True), primary_key=False, nullable=False),
    )

def downgrade():
    """Usuwa tabele w kolejności odwrotnej do zależności."""
    op.drop_table('simulations')
    op.drop_table('mail_outbox')
    op.drop_table('measurements')
    op.drop_table('alerts')
    op.drop_table('spc_configs')
    op.drop_table('results')
    op.drop_table('notification_rules')
    op.drop_table('lab_sessions')
    op.drop_table('dispositions')
    op.drop_table('characteristics')
    op.drop_table('orders')
    op.drop_table('login_sessions')
    op.drop_table('historical_rows')
    op.drop_table('audit')
    op.drop_table('article_configs')
    op.drop_table('users')
    op.drop_table('methods')
    op.drop_table('login_attempts')
    op.drop_table('articles')
