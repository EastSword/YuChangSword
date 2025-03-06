// RSA示例
const keyPair = RSA.generate(2048);
const cipher = new PKCS1_OAEP(keyPair.publicKey);