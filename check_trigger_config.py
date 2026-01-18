#!/usr/bin/env python3
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

engine = create_engine('postgresql://pplmeta:pplmeta123@localhost:5432/ppl_meta_db')
Session = sessionmaker(bind=engine)
db = Session()

# Get Seniors Activity trigger
trigger = db.execute(text("SELECT uuid, name, demographic_conditions, camera_device_id, action_uuid, is_active, cooldown_seconds FROM triggers WHERE name = 'Seniors Activity'")).fetchone()
if trigger:
    print('🎯 TRIGGER: Seniors Activity')
    print(f'   UUID: {trigger[0]}')
    print(f'   Conditions: {trigger[2]}')
    print(f'   Camera: {trigger[3]}')
    print(f'   Action UUID: {trigger[4]}')
    print(f'   Active: {trigger[5]}')
    print(f'   Cooldown: {trigger[6]}s')
    print()
    
    # Get linked action
    if trigger[4]:
        action = db.execute(text('SELECT uuid, name, action_type, action_config FROM user_trigger_actions WHERE uuid = :action_uuid'), {'action_uuid': trigger[4]}).fetchone()
        if action:
            print('📧 LINKED ACTION:')
            print(f'   Name: {action[1]}')
            print(f'   Type: {action[2]}')
            print(f'   Config: {action[3]}')
        else:
            print('❌ No action found')
    else:
        print('❌ No action assigned')
else:
    print('❌ Trigger not found')

db.close()
