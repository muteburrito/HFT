import streamlit as st

def render(analysis):
    st.subheader("Option Chain Data")
    chain = analysis.get('chain')
    ltp = analysis.get('ltp', 0)
    
    if chain is not None and not chain.empty:
        # Find ATM Strike for highlighting
        chain['diff'] = abs(chain['strike_price'] - ltp)
        atm_strike = chain.loc[chain['diff'].idxmin()]['strike_price']
        
        # Highlight ATM
        def highlight_atm(row):
            if row['strike_price'] == atm_strike:
                return ['background-color: #ffffb3'] * len(row)
            return [''] * len(row)
            
        st.dataframe(chain.drop(columns=['diff']).style.apply(highlight_atm, axis=1))
    else:
        st.write("No Data Available")
