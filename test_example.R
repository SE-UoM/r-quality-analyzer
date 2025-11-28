# Example R file for testing
library(dplyr)
library(ggplot2)

# Simple function
calculate_mean <- function(x) {
  if (length(x) == 0) {
    return(0)
  }
  sum(x) / length(x)
}

# More complex function with multiple conditions
analyze_data <- function(data, threshold = 10) {
  if (is.null(data) || nrow(data) == 0) {
    stop("Data is empty")
  }
  
  result <- list()
  
  for (i in 1:ncol(data)) {
    col_data <- data[, i]
    
    if (is.numeric(col_data)) {
      mean_val <- calculate_mean(col_data)
      
      if (mean_val > threshold) {
        result[[i]] <- "high"
      } else if (mean_val > threshold / 2) {
        result[[i]] <- "medium"
      } else {
        result[[i]] <- "low"
      }
    } else {
      result[[i]] <- "non-numeric"
    }
  }
  
  return(result)
}

# Function with package namespace usage
plot_results <- function(data) {
  ggplot2::ggplot(data, aes(x = x, y = y)) +
    geom_point() +
    theme_minimal()
}

# Another function
process_data <- function(input) {
  output <- input %>%
    filter(value > 0) %>%
    mutate(new_col = value * 2)
  
  return(output)
}



