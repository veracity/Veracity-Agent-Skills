# Production Environment Setup (Redis + KeyVault)

For non-Development environments, configure:

## 1. Redis (Distributed Cache & Data Protection Key Store)

Set the connection string:
```json
"ConnectionStrings": {
  "Redis": "your-redis-host:6380,password=...,ssl=True,abortConnect=False"
}
```

## 2. Azure Key Vault (Data Protection Key Encryption)

Set the data protection key URI:
```json
"DataProtection": {
  "KeyVaultKeyUri": "https://<your-keyvault-name>.vault.azure.net/keys/<your-key-name>"
}
```

## 3. Veracity Credentials

Store `ClientId`, `ServiceId`, `ClientSecret`, and `SubscriptionKey` in Azure Key Vault or environment variables. `ClientId` and `ServiceId` are not secrets, but keep `ClientSecret` and `SubscriptionKey` out of `appsettings.json` for production. (`ServiceId` is only needed when the V4 policy-validation endpoint is used. Note that `ServiceId` is a top-level configuration key, not part of the `Veracity` section.)

Example using environment variables:
```
Veracity__ClientId=<your-client-id>
ServiceId=<your-service-id>
Veracity__ClientSecret=<your-client-secret>
Veracity__SubscriptionKey=<your-subscription-key>
```
