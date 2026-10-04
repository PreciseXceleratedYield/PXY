        # 4. Construct Output Price Data Engine (FIXED LENGTH INTERFACE WITH UNIQUE TIMESTAMPS)
        renko_df = pd.DataFrame()
        renko_df['Open'] = renko_ops
        renko_df['Close'] = renko_cl_list
        renko_df['High'] = np.maximum(np.array(renko_ops), np.array(renko_cl_list))
        renko_df['Low'] = np.minimum(np.array(renko_ops), np.array(renko_cl_list))
