#include <algorithm>
#include <atomic>
#include <cstdint>
#include <iostream>
#include <thread>
#include <vector>

using u32 = std::uint32_t;
using u64 = std::uint64_t;

struct Field {
    u64 p;

    explicit Field(u64 prime) : p(prime) {}

    inline u32 mul(u32 a, u32 b) const {
        return u32((u64(a) * u64(b)) % p);
    }

    inline u32 add(u32 a, u32 b) const {
        const u64 sum = u64(a) + b;
        return u32(sum >= p ? sum - p : sum);
    }

    inline u32 sub(u32 a, u32 b) const {
        return a >= b ? a - b : u32(u64(a) + p - b);
    }
};

int main() {
    int n;
    u64 prime;
    if (!(std::cin >> n >> prime) || n < 1 || n > 16) {
        std::cerr << "expected: n prime followed by n*n entries\n";
        return 2;
    }

    Field field(prime);
    std::vector<u32> matrix(std::size_t(n) * n);
    for (u32& entry : matrix) {
        u64 value;
        if (!(std::cin >> value)) {
            std::cerr << "missing matrix entry\n";
            return 2;
        }
        entry = u32(value % prime);
    }

    const int limit = 1 << n;
    std::vector<std::vector<u32>> masks(n + 1);
    std::vector<std::vector<int>> rank(n + 1, std::vector<int>(limit, -1));
    for (int mask = 0; mask < limit; ++mask) {
        const int size = __builtin_popcount(u32(mask));
        rank[size][mask] = int(masks[size].size());
        masks[size].push_back(u32(mask));
    }

    std::vector<u32> previous;
    const unsigned workers =
        std::max(1u, std::min(10u, std::thread::hardware_concurrency()));
    u64 checked = 0;

    for (int size = 1; size <= n; ++size) {
        const std::size_t combinations = masks[size].size();
        const std::size_t previous_combinations =
            size == 1 ? 0 : masks[size - 1].size();
        std::vector<u32> current(combinations * combinations);
        std::atomic<bool> found_zero(false);
        std::atomic<std::size_t> zero_index(0);
        std::vector<std::thread> threads;
        const std::size_t rows_per_worker =
            (combinations + workers - 1) / workers;

        for (unsigned worker = 0; worker < workers; ++worker) {
            const std::size_t begin = worker * rows_per_worker;
            const std::size_t end = std::min(combinations, begin + rows_per_worker);
            if (begin >= end) break;

            threads.emplace_back([&, begin, end, size, combinations,
                                  previous_combinations]() {
                for (std::size_t row_index = begin; row_index < end; ++row_index) {
                    const u32 row_mask = masks[size][row_index];
                    const int row = __builtin_ctz(row_mask);
                    const u32 reduced_rows = row_mask ^ (u32(1) << row);
                    const std::size_t reduced_row_rank =
                        size == 1 ? 0 : std::size_t(rank[size - 1][reduced_rows]);

                    for (std::size_t column_index = 0;
                         column_index < combinations;
                         ++column_index) {
                        const u32 column_mask = masks[size][column_index];
                        u32 determinant = 0;

                        if (size == 1) {
                            determinant = matrix[
                                std::size_t(row) * n + __builtin_ctz(column_mask)
                            ];
                        } else {
                            u32 remaining = column_mask;
                            int position = 0;
                            while (remaining) {
                                const int column = __builtin_ctz(remaining);
                                const u32 bit = u32(1) << column;
                                const u32 reduced_columns = column_mask ^ bit;
                                const std::size_t reduced_column_rank =
                                    std::size_t(rank[size - 1][reduced_columns]);
                                const u32 term = field.mul(
                                    matrix[std::size_t(row) * n + column],
                                    previous[
                                        reduced_row_rank * previous_combinations
                                        + reduced_column_rank
                                    ]
                                );
                                determinant = (position & 1)
                                    ? field.sub(determinant, term)
                                    : field.add(determinant, term);
                                remaining ^= bit;
                                ++position;
                            }
                        }

                        const std::size_t index =
                            row_index * combinations + column_index;
                        current[index] = determinant;
                        if (determinant == 0) {
                            bool expected = false;
                            if (found_zero.compare_exchange_strong(expected, true)) {
                                zero_index.store(index);
                            }
                        }
                    }
                }
            });
        }

        for (auto& thread : threads) thread.join();
        checked += current.size();

        if (found_zero) {
            const std::size_t index = zero_index.load();
            std::cout << "ZERO_MINOR size=" << size
                      << " row_mask=" << masks[size][index / combinations]
                      << " column_mask=" << masks[size][index % combinations]
                      << std::endl;
            return 1;
        }

        previous = std::move(current);
    }

    std::cout << "checked_minors " << checked << std::endl;
    std::cout << "ALL_NONEMPTY_SQUARE_MINORS_NONZERO" << std::endl;
    return 0;
}
