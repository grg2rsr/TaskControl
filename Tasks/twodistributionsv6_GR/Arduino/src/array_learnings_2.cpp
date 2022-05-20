#include <iostream>
using namespace std;

int *l;


// main function to call above defined function.
int main () {

    float q = 2.0;

    int k[(int) q];
    k[0] = 1;
    k[1] = 2;
    for (int i = 0; i < 3;i++){
        cout << k[i] << endl;
    }

    return 0;
}

/*

also read this about decaying
https://stackoverflow.com/questions/19894686/getting-size-of-array-from-pointer-c

*/