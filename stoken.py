from itsdangerous import URLSafeTimedSerializer
salt='Otpverify'
def endata(data):
    serializer = URLSafeTimedSerializer('code123')
    return serializer.dumps(data,salt=salt)

def dndata(data):
    serializer = URLSafeTimedSerializer('code123')
    return serializer.loads(data,salt=salt)