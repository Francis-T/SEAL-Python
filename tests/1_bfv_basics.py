from seal import *


def print_example_banner(title):
    title_length = len(title)
    banner_length = title_length + 2 * 10
    banner_top = "+" + "-" * (banner_length - 2) + "+"
    banner_middle = "|" + ' ' * 9 + title + ' ' * 9 + "|"
    print(banner_top)
    print(banner_middle)
    print(banner_top)


def print_parameters(context):
    context_data = context.key_context_data()
    if context_data.parms().scheme() == scheme_type.BFV:
        scheme_name = "BFV"
    elif context_data.parms().scheme() == scheme_type.CKKS:
        scheme_name = "CKKS"
    else:
        scheme_name = "unsupported scheme"
    print("/")
    print("| Encryption parameters:")
    print("| scheme: " + scheme_name)
    print("| poly_modulus_degree: " +
          str(context_data.parms().poly_modulus_degree()))
    print("| coeff_modulus size: ", end="")
    coeff_modulus = context_data.parms().coeff_modulus()
    coeff_modulus_sum = 0
    for j in coeff_modulus:
        coeff_modulus_sum += j.bit_count()
    print(str(coeff_modulus_sum) + "(", end="")
    for i in range(len(coeff_modulus) - 1):
        print(str(coeff_modulus[i].bit_count()) + " + ", end="")
    print(str(coeff_modulus[-1].bit_count()) + ") bits")
    if context_data.parms().scheme() == scheme_type.BFV:
        print("| plain_modulus: " +
              str(context_data.parms().plain_modulus().value()))
    print("\\")


def example_bfv_basics():
    print_example_banner("Example: BFV Basics")
    parms = EncryptionParameters(scheme_type.BFV)

    poly_modulus_degree = 4096
    parms.set_poly_modulus_degree(poly_modulus_degree)
    parms.set_coeff_modulus(CoeffModulus.BFVDefault(poly_modulus_degree))
    parms.set_plain_modulus(256)

    context = SEALContext.Create(parms)

    print("-" * 50)
    print("Set encryption parameters and print")
    print_parameters(context)
    print("~~~~~~ A naive way to calculate 2(x^2+1)(x+1)^2. ~~~~~~")

    keygen = KeyGenerator(context)
    public_key = keygen.public_key()
    secret_key = keygen.secret_key()

    encryptor = Encryptor(context, public_key)

    evaluator = Evaluator(context)

    decryptor = Decryptor(context, secret_key)

    print("-" * 50)
    x = "6"
    x_plain = Plaintext(x)
    print("Express x = " + x + " as a plaintext polynomial 0x" +
          x_plain.to_string() + ".")

    print("-" * 50)
    x_encrypted = Ciphertext()
    print("Encrypt x_plain to x_encrypted.")
    encryptor.encrypt(x_plain, x_encrypted)

    print("    + size of freshly encrypted x: " + str(x_encrypted.size()))

    print("    + noise budget in freshly encrypted x: " +
          str(decryptor.invariant_noise_budget(x_encrypted)) + " bits")

    x_decrypted = Plaintext()
    print("    + decryption of x_encrypted: ", end="")
    decryptor.decrypt(x_encrypted, x_decrypted)
    print("0x" + x_decrypted.to_string() + " ...... Correct.")

    print("-"*50)
    print("Compute x_sq_plus_one (x^2+1).")

    x_sq_plus_one = Ciphertext()
    evaluator.square(x_encrypted, x_sq_plus_one)
    plain_one = Plaintext("1")
    evaluator.add_plain_inplace(x_sq_plus_one, plain_one)

    print("    + size of x_sq_plus_one: " + str(x_sq_plus_one.size()))
    print("    + noise budget in x_sq_plus_one: " +
          str(decryptor.invariant_noise_budget(x_sq_plus_one)) + " bits")

    decrypted_result = Plaintext()
    print("    + decryption of x_sq_plus_one: ", end="")
    decryptor.decrypt(x_sq_plus_one, decrypted_result)
    print("0x" + decrypted_result.to_string() + " ...... Correct.")

    '''
	Next, we compute (x + 1)^2.
	'''
    print("-"*50)
    print("Compute x_plus_one_sq ((x+1)^2).")
    x_plus_one_sq = Ciphertext()
    evaluator.add_plain(x_encrypted, plain_one, x_plus_one_sq)
    evaluator.square_inplace(x_plus_one_sq)
    print("    + size of x_plus_one_sq: " + str(x_plus_one_sq.size()))
    print("    + noise budget in x_plus_one_sq: " +
          str(decryptor.invariant_noise_budget(x_plus_one_sq)) + " bits")
    decryptor.decrypt(x_plus_one_sq, decrypted_result)
    print("    + decryption of x_plus_one_sq: 0x" +
          decrypted_result.to_string() + " ...... Correct.")

    '''
	Finally, we multiply (x^2 + 1) * (x + 1)^2 * 2.
	'''
    print("-"*50)
    print("Compute encrypted_result (2(x^2+1)(x+1)^2).")
    encrypted_result = Ciphertext()
    plain_two = Plaintext("2")
    evaluator.multiply_plain_inplace(x_sq_plus_one, plain_two)
    evaluator.multiply(x_sq_plus_one, x_plus_one_sq, encrypted_result)
    print("    + size of encrypted_result: " + str(encrypted_result.size()))
    print("    + noise budget in encrypted_result: " +
          str(decryptor.invariant_noise_budget(encrypted_result)) + " bits")
    print("NOTE: Decryption can be incorrect if noise budget is zero.")
    print("\n~~~~~~ A better way to calculate 2(x^2+1)(x+1)^2. ~~~~~~")

    print("-"*50)
    print("Generate relinearization keys.")
    relin_keys = keygen.relin_keys()

    '''
	We now repeat the computation relinearizing after each multiplication.
	'''
    print("-"*50)
    print("Compute and relinearize x_squared (x^2),")
    print(" "*13 + "then compute x_sq_plus_one (x^2+1)")
    x_squared = Ciphertext()
    evaluator.square(x_encrypted, x_squared)
    print("    + size of x_squared: " + str(x_squared.size()))
    evaluator.relinearize_inplace(x_squared, relin_keys)
    print("    + size of x_squared (after relinearization): " + str(x_squared.size()))
    evaluator.add_plain(x_squared, plain_one, x_sq_plus_one)
    print("    + noise budget in x_sq_plus_one: " +
          str(decryptor.invariant_noise_budget(x_sq_plus_one)) + " bits")
    decryptor.decrypt(x_sq_plus_one, decrypted_result)
    print("    + decryption of x_sq_plus_one: 0x" +
          decrypted_result.to_string() + " ...... Correct.")

    print("-"*50)
    x_plus_one = Ciphertext()
    print("Compute x_plus_one (x+1),")
    print(" "*13 + "then compute and relinearize x_plus_one_sq ((x+1)^2).")
    evaluator.add_plain(x_encrypted, plain_one, x_plus_one)
    evaluator.square(x_plus_one, x_plus_one_sq)
    print("    + size of x_plus_one_sq: " + str(x_plus_one_sq.size()))
    evaluator.relinearize_inplace(x_plus_one_sq, relin_keys)
    print("    + noise budget in x_plus_one_sq: " +
          str(decryptor.invariant_noise_budget(x_plus_one_sq)) + " bits")
    decryptor.decrypt(x_plus_one_sq, decrypted_result)
    print("    + decryption of x_plus_one_sq: 0x" +
          decrypted_result.to_string() + " ...... Correct.")

    print("-"*50)
    print("Compute and relinearize encrypted_result (2(x^2+1)(x+1)^2).")
    evaluator.multiply_plain_inplace(x_sq_plus_one, plain_two)
    evaluator.multiply(x_sq_plus_one, x_plus_one_sq, encrypted_result)
    print("    + size of encrypted_result: " + str(encrypted_result.size()))
    evaluator.relinearize_inplace(encrypted_result, relin_keys)
    print("    + size of encrypted_result (after relinearization): " +
          str(encrypted_result.size()))
    print("    + noise budget in encrypted_result: " +
          str(decryptor.invariant_noise_budget(encrypted_result)) + " bits")
    print("\nNOTE: Notice the increase in remaining noise budget.")

    print("-"*50)
    print("Decrypt encrypted_result (2(x^2+1)(x+1)^2).")
    decryptor.decrypt(encrypted_result, decrypted_result)
    print("    + decryption of 2(x^2+1)(x+1)^2 = 0x" +
          decrypted_result.to_string() + " ...... Correct.")


if __name__ == '__main__':
    example_bfv_basics()
