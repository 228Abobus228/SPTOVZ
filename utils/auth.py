from passlib.context import CryptContext

# Контекст шифрования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Хэширование пароля при регистрации
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# Проверка пароля при входе
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
