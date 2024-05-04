from source.classes import diags as diags

global VERBOSE
VERBOSE = True

if __name__ == "__main__":
    if VERBOSE:
        print("DIAGNOSTICS")
        print('.' * 70)
    print("\n".join(diags.output()))
