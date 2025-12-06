import redis
import json

r = redis.Redis(decode_responses=True)
keys = r.keys('waitfor:join_parallel_checks:inputs')
print('Keys found:', keys)
for key in keys:
    data = r.hgetall(key)
    print(f'\nKey: {key}')
    for field, value in data.items():
        print(f'  Field: {field}')
        try:
            parsed = json.loads(value)
            print(f'  Value type: {type(parsed)}')
            if isinstance(parsed, dict):
                for k, v in parsed.items():
                    print(f'    {k}: {type(v).__name__} = {str(v)[:50]}')
        except Exception as e:
            print(f'  Parse error: {e}')
            print(f'  Value: {value[:200]}...')
