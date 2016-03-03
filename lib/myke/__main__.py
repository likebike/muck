import sys
import myke

if __name__ == '__main__':
    assert len(sys.argv) == 3
    myke.build(sys.argv[1], sys.argv[2])

