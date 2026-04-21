from enum import Enum


class TransactionType(str, Enum):
    DEPOSIT = "deposit"  # пополнение баланса пользователем
    DEBIT = "debit"  # списание за предсказание
    ADMIN_DEPOSIT = "admin_deposit"  # пополнение администратором
