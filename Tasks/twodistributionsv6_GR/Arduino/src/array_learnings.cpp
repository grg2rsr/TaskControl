#include <iostream>
#include <ctime>

using namespace std;

void normalize_p(float * p, int n){
    // in place normalization, pointer variant

    float p_sum = 0;
    for (int i = 0; i < n; i++){
        p_sum += *(p+i);
    }
    cout << p_sum << endl;
    for (int i = 0; i < n; i++){
        *(p+i) = *(p+i) / p_sum;
    }
}

void get_p_obs(int* counts, float* res, int n){
    // pointerized version - turns counts into a prob dist

    float sum = 0;
    for (int i = 0; i < n; i++){
        sum += counts[i];
        // sum += *(counts+i);
    }

    for (int i = 0; i < n; i++){
        res[i] = *(counts+i) / sum;
    }
}

// float* get_p_obs(int* counts, float* res, int n){
//     // pointerized version - turns counts into a prob dist

//     float sum = 0;
//     for (int i = 0; i < n; i++){
//         sum += counts[i];
//         // sum += *(counts+i);
//     }

//     // float p_obs[n];
//     for (int i = 0; i < n; i++){
//         res[i] = *(counts+i) / sum;
//     }
//     // static makes it survive
//     // static float *  p_obsr = &p_obs[0];
//     return &res[0];
// }

float* indexing_test(float* p, int n){
    for (int i = 0; i < n; i++){
        //*(p+i) = *(p+i) / 2;
        p[i] = p[i] / 2;
    }
    return p;
}

// main function to call above defined function.
int main () {

    // passing an array to a function
    /*
    logic here is: passing the pointer to the first element and the number of elements
    function call signature accepts pointer of correct type
    */
    float p[] = {1 ,2, 2, 3, 1};
    normalize_p(&p[0], 5);

    // example: dereferencing pointers into an allocated array
    /*
    not sure when this could be useful though. Allows [] syntax
    */
    float P[5];
    for ( int i = 0; i < 5; i++ ) {
        P[i] = *(p+i);
    }

    // needed: a function returning an array
    // solution: create and preallocate memory and pass it
    // turning to everything in place operation
    int counts[] = {5, 15, 15, 15, 5};
    int n_counts = sizeof(counts)/sizeof(counts[0]);
    float res[n_counts]; // memory allocation
    // WORKS

    get_p_obs(&counts[0], &res[0], 5);

    // for ( int i = 0; i < 5; i++ ) {
    //     cout << *(p_obsr+i) << endl;
    // }

    // for ( int i = 0; i < 5; i++ ) {
    //     cout << res[i] << endl;
    // }

    // syntax explorations
    float q[] = {1,2,3,4,5};

    // float* qp = indexing_test(&q[0], 5);
    float* qp = indexing_test(q, 5); // q decays to &q[0]
    // if an array is passed to a function that receives a pointer, 
    // the pointer to the first element is passed and not the array

    // dereferencing
    for ( int i = 0; i < 5; i++ ) {
        //cout << *(qp+i) << endl;
        cout << qp[i] << endl; // qp[i] and *(qp+i) are equivalent?
    }



    return 0;
}

/*

also read this about decaying
https://stackoverflow.com/questions/19894686/getting-size-of-array-from-pointer-c

*/