import json
import os
import sys

from ida_domain import Database

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tqdm import tqdm
from alive_constants import *
from parser import get_event_mappings, string_pool
from event_mapping_pb2 import EventMappings, EventMapping as PBEventMapping, ConditionalReturn
import msgpack
 
def extract(db_path):
    with Database.open(path=db_path, save_on_close=False) as db:
        mappings = db.functions.get_at(PLOT_MAPPINGS_ADDR)
        print('name: ' + mappings.name)
        mappings_instructions = list(db.functions.get_instructions(mappings))
        print('total instructions: ' + str(len(mappings_instructions)))
        print('fetching event metadata...')
        event_mappings = get_event_mappings(db.functions.get_pseudocode(mappings))
        event_mappings = [mapping for mapping in event_mappings if mapping.evId <= 500 and mapping.evId not in [400, 0] and mapping.evFunc != "sub_431E00"]
        print(f'✓ gathered {len(event_mappings)} event metadata')

        events = []
        for mapping in tqdm(event_mappings[:], desc='Processing events'):
            mapping.get_instructions(db)
            # tqdm.write(f'Fetched Event {mapping.evId} instructions: {len(mapping.instructions)}')
            if len(mapping.return_values) == 0: continue
            events.append(mapping)
        
        # return

        print("Got events", len(events))
        events = sorted(events, key=lambda x: x.evId)

        # Create protobuf EventMappings container
        event_mappings_pb = EventMappings()
        event_mappings_pb.textPool.extend(string_pool)

        with open('events.json', 'w', encoding='utf-8') as f:
            json.dump({'textPool': string_pool, 'events': [mapping.to_dict() for mapping in events]}, f, ensure_ascii=False)

        with open('events.indent.json', 'w', encoding='utf-8') as f:
            json.dump({'textPool': string_pool, 'events': [mapping.to_dict() for mapping in events]}, f, ensure_ascii=False, indent=4)

        with open('events.msgpack', 'wb') as f:
            f.write(msgpack.packb({'textPool': string_pool, 'events': [mapping.to_dict() for mapping in events]}))
        
        for mapping in events:
            # Convert EventMapping to protobuf using the new method
            pb_mapping = mapping.to_protobuf()
            event_mappings_pb.events.append(pb_mapping)

        root = PBEventMapping()
        root.evId = 512
        root.flag1 = 0
        root.evFunc = "(root)"
        root.hasChoices = False

        root_conditional_return = ConditionalReturn()
        root_conditional_return.passedEvIds.extend([-4])
        root_conditional_return.returnValue = 401
        root.conditionalReturns.append(root_conditional_return)
        root_conditional_return = ConditionalReturn()
        root_conditional_return.passedEvIds.extend([-3, -2, -1])
        root_conditional_return.returnValue = 69
        root.conditionalReturns.append(root_conditional_return)
        root_conditional_return = ConditionalReturn()
        root.returnValues.append(1)
        event_mappings_pb.events.append(root)

        # Save as protobuf binary format
        with open('events.pb', 'wb') as f:
            f.write(event_mappings_pb.SerializeToString())

    tqdm.write('✓ Database closed')


if __name__ == '__main__':
    extract("./alive.exe.i64")