#include <iostream>
#include <algorithm>
#include <vector>
using namespace std;

int add(int a, int b) {
    return a + b;
}

long long factorial(int n) {
    return (n <= 1) ? 1 : n * factorial(n - 1);
}

long binpow(long n, long k){

    n == k ? 1 : n * binpow(n, k - 1);
} 

int main() {
    // Gõ ở đây: "cout << " và xem có gợi ý không
    cout << add(5, 7) << endl;
    return 0;
}
