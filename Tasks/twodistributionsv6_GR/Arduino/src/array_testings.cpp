#include <stdio.h>
#include <stdlib.h>
#include <iostream>
//#include <ctime>
#include <time.h>

using namespace std;

unsigned int sample_p(float* p, int n){
    // pointer version
    // returns index
    float r = rand() / (float) RAND_MAX;
    // float r = (rand() % 10000) / 10000.0;
    // float r = random(0,10000) / 10000;

    float p_cumsum;
    for (int i = 0; i < n; i++){
        p_cumsum = 0;
        for (int j = 0; j <= i; j++){
            p_cumsum += *(p+j);
        }
        if (r < p_cumsum){
            return i;
        }
    }
    return n-1;
}

void normalize_p(float* p, int n){
    // in place normalization
    // pointer variant
    float p_sum = 0;
    for (int i = 0; i < n; i++){
        p_sum += *(p+i);
    }
    for (int i = 0; i < n; i++){
        *(p+i) = *(p+i) / p_sum;
    }
}


void clip_p(float* p, int n){
    // in place clipping from 0,1
    // only makes sense if afterwards renormalized - so done here too

    for (int i = 0; i < n; i++){
        if (*(p+i) < 0){
            *(p+i) = 0.0;
        }
        if (*(p+i) > 1){
            *(p+i) = 1.0;
        }
    }
    // for (int i = 0; i < n; i++){
    //     cout << *(p+i) << endl;
    // }
    normalize_p(p, n); // also inplace

}

void calc_p_obs(int* counts, float* res, int n){
    // pointerized version - turns counts into a prob dist
    // res = p_obs

    float sum = 0;
    for (int i = 0; i < n; i++){
        // sum += counts[i];
        sum += *(counts+i);
    }

    for (int i = 0; i < n; i++){
        res[i] = *(counts+i) / sum;
    }
}

void calc_p_adj(float* p_obs, float* p_des, float* res, int n){
    // p_des = p_desired
    // p_obs = p_observed
    // n = number of elements
    for (int i = 0; i < n; i++){
        res[i] = (float) *(p_des+i) - *(p_obs+i);
    }



    //return &res[0]; // explicitly returning the reference of first element
}

int sample_p_adj(float* p_des, int* counts, int n){
    // adjusted sampling marga style
    // faster convergence towards p_des
    float p_obs[n];
    calc_p_obs(counts, &p_obs[0], n); //counts is already a pointer

    float p_adj[n];
    calc_p_adj(&p_obs[0], p_des, &p_adj[0], n); // p_des is already a pointer
    
    clip_p(&p_adj[0], n); // and normalize
    
    int j = sample_p(&p_adj[0], n);
    return j;
}


// main function to call above defined function.
int main () {
    
    srand(time(NULL));

    float p[5] = {1,2,3,2,1};
    int counts[5] = {0, 0, 0, 0, 0};
    normalize_p(&p[0], 5);
  
    for ( int i = 0; i < 250; i++ ) {
        // cout << p[i] << endl;
        
        // unadjusted sampling
        // int j = sample_p(&p[0], 5);
        // counts[j]++;
        // cout << j << endl;
        
        // adjusted sampling
        if (i < 10){
            int j = sample_p(&p[0], 5);
            counts[j]++;
            cout << j << endl;
        }
        else{
            int j = sample_p_adj(&p[0], &counts[0], 5);
            counts[j]++;
            cout << j << endl;
        }
    }
    return 0;
}

/*

also read this about decaying
https://stackoverflow.com/questions/19894686/getting-size-of-array-from-pointer-c

*/

